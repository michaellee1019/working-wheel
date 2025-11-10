from typing import ClassVar, Final, Mapping, Optional, Sequence, Tuple
import os
import json
import datetime

from typing_extensions import Self
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.services.generic import *
from viam.components.motor import Motor
from viam.utils import ValueTypes

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Status constants representing physical wheel positions (cannot be changed without hardware modification)
IN_MEETING = 0
AVAILABLE = 1
FOCUS_TIME = 2
GOING_TO_EVENT = 3
WORK_FROM_HOME = 4
OUT_OF_OFFICE = 5

# Precedence order (lower number = higher priority) - separate from physical positions
# When multiple events overlap, this determines which status is shown
STATUS_PRECEDENCE = {
    OUT_OF_OFFICE: 0,      # Highest priority
    IN_MEETING: 1,
    FOCUS_TIME: 2,
    GOING_TO_EVENT: 3,
    WORK_FROM_HOME: 4,
    AVAILABLE: 5           # Lowest priority
}


class GoogleCalenderService(Generic, EasyResource):
    # To enable debug-level logging, either run viam-server with the --debug option,
    # or configure your resource/machine to display debug logs.
    MODEL: ClassVar[Model] = Model(
        ModelFamily("michaellee1019", "working-wheel"), "google-calender-service"
    )

    motor: Motor
    needs_reset: bool
    current_position: int  # 0-5 corresponding to the 6 wheel positions
    reverse_motor: bool = False

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        """This method creates a new instance of this Generic service.
        The default implementation sets the name from the `config` parameter and then calls `reconfigure`.

        Args:
            config (ComponentConfig): The configuration for this resource
            dependencies (Mapping[ResourceName, ResourceBase]): The dependencies (both required and optional)

        Returns:
            Self: The resource
        """
        return super().new(config, dependencies)

    @classmethod
    def validate_config(
        cls, config: ComponentConfig
    ) -> Tuple[Sequence[str], Sequence[str]]:
        """This method allows you to validate the configuration object received from the machine,
        as well as to return any required dependencies or optional dependencies based on that `config`.

        Args:
            config (ComponentConfig): The configuration for this resource

        Returns:
            Tuple[Sequence[str], Sequence[str]]: A tuple where the
                first element is a list of required dependencies and the
                second element is a list of optional dependencies
        """

        if "motor" not in config.attributes:
            raise ValueError("motor is required")
        
        return [], [config.attributes["motor"]]

    def reconfigure(
        self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ):
        """This method allows you to dynamically update your service when it receives a new `config` object.

        Args:
            config (ComponentConfig): The new configuration
            dependencies (Mapping[ResourceName, ResourceBase]): Any dependencies (both required and optional)
        """
        self.motor = dependencies[Motor.get_resource_name(config.attributes["motor"])]
        if "reverse_motor" in config.attributes:
            self.reverse_motor = config.attributes["reverse_motor"]
        # On reconfiguration, mark that the wheel needs to be reset
        # This will trigger a full rotation on the first next turn_wheel call
        self.needs_reset = True
        self.current_position = OUT_OF_OFFICE  # Will be set after reset
        
        self.logger.info("Service reconfigured - wheel will reset on next turn_wheel call")
        return super().reconfigure(config, dependencies)

    async def do_command(
        self,
        command: Mapping[str, ValueTypes],
        *,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Mapping[str, ValueTypes]:
        """Handle custom commands for the Google Calendar service.
        
        Supported commands:
        - set_credentials: Store Google OAuth credentials
        - test_calendar_status: Detect calendar status and return appropriate event type
        - turn_wheel: Turn the wheel to the appropriate position based on calendar
        - test_wheel: Manually move wheel to a specific position for testing
        """
        if "set_credentials" in command:
            result = await self.set_credentials(command["set_credentials"])
            return {"success": result}
        
        if "test_calendar_status" in command:
            result = await self.get_calendar_status()
            return result

        if "turn_wheel" in command:
            result = await self.turn_wheel()
            return result

        if "test_wheel" in command:
            # Extract status name from command
            status_name = command.get("test_wheel")
            result = await self.test_wheel(status_name=status_name)
            return result
        
        self.logger.error("`do_command` received unknown command")
        raise NotImplementedError(f"Unknown command: {list(command.keys())}")

    async def set_credentials(self, credentials_payload: ValueTypes) -> bool:
        """Store Google OAuth credentials in the module data directory.
        
        Args:
            credentials_payload: The OAuth credentials JSON (as string or dict)
                                that would normally be stored in token.json
        
        Returns:
            bool: True if credentials were successfully stored, False otherwise
        """
        try:
            # Get the module data directory from environment variable
            module_data_dir = os.environ.get('VIAM_MODULE_DATA')
            if not module_data_dir:
                self.logger.error("VIAM_MODULE_DATA environment variable not set")
                return False
            
            # Ensure the directory exists
            os.makedirs(module_data_dir, exist_ok=True)
            
            # Path to store the credentials
            token_path = os.path.join(module_data_dir, 'token.json')
            
            # Convert credentials to JSON string if it's a dict
            if isinstance(credentials_payload, dict):
                credentials_json = json.dumps(credentials_payload)
            elif isinstance(credentials_payload, str):
                # Validate it's valid JSON
                json.loads(credentials_payload)
                credentials_json = credentials_payload
            else:
                self.logger.error(f"Invalid credentials payload type: {type(credentials_payload)}")
                return False
            
            # Write credentials to file
            with open(token_path, 'w') as token_file:
                token_file.write(credentials_json)
            
            self.logger.info(f"Successfully stored credentials to {token_path}")
            return True
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in credentials payload: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error storing credentials: {e}")
            return False

    async def get_calendar_status(self) -> Mapping[str, ValueTypes]:
        """Detect the current calendar status and return the appropriate event type.
        
        Special event types (outOfOffice, focusTime, workingLocation) are checked before
        generic busy events. When multiple events are detected, precedence is determined
        by STATUS_PRECEDENCE (not by physical position number).
        
        Physical wheel positions (cannot be changed without hardware modification):
        0. IN_MEETING - Currently in a busy event (generic, not a special type)
        1. AVAILABLE - No matching events
        2. FOCUS_TIME - Currently in a focus time block (special event type)
        3. GOING_TO_EVENT - Busy event starting in next 5 minutes (generic)
        4. WORK_FROM_HOME - Working from home location (special working location)
        5. OUT_OF_OFFICE - Out of office event (special event type)
        
        Priority order (when multiple events overlap):
        1. OUT_OF_OFFICE (highest priority)
        2. IN_MEETING
        3. FOCUS_TIME
        4. GOING_TO_EVENT
        5. WORK_FROM_HOME
        6. AVAILABLE (lowest priority)
        
        Returns:
            dict: Status information including status code, name, and event details
        """
        try:
            # Load credentials from the module data directory
            module_data_dir = os.environ.get('VIAM_MODULE_DATA')
            if not module_data_dir:
                self.logger.error("VIAM_MODULE_DATA environment variable not set")
                return {"error": "VIAM_MODULE_DATA not set"}
            
            token_path = os.path.join(module_data_dir, 'token.json')
            if not os.path.exists(token_path):
                self.logger.error(f"Token file not found at {token_path}")
                return {"error": "Credentials not set. Please run set_credentials first."}
            
            # Load and refresh credentials if needed
            creds = Credentials.from_authorized_user_file(token_path)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed credentials
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            # Build the Calendar service
            service = build('calendar', 'v3', credentials=creds)
            
            # Get current time
            now = datetime.datetime.utcnow()
            now_iso = now.isoformat() + 'Z'
            
            # Get start and end of current day
            start_of_day = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
            end_of_day = start_of_day + datetime.timedelta(days=1)
            start_of_day_iso = start_of_day.isoformat() + 'Z'
            end_of_day_iso = end_of_day.isoformat() + 'Z'
            
            # Fetch events for the current day
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_of_day_iso,
                timeMax=end_of_day_iso,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            
            self.logger.debug(f"Found {len(events)} events for today")
            
            # Check for events in order of precedence
            detected_status = self._check_calendar_status(events, now)
            
            return detected_status
            
        except HttpError as error:
            self.logger.error(f"Google Calendar API error: {error}")
            return {"error": f"Calendar API error: {error}"}
        except Exception as e:
            self.logger.error(f"Error in turn_wheel: {e}")
            return {"error": f"Unexpected error: {e}"}
    
    def _check_calendar_status(self, events: list, now: datetime.datetime) -> dict:
        """Check calendar events and determine status based on precedence rules.
        
        Args:
            events: List of calendar events
            now: Current datetime
            
        Returns:
            dict: Status information
        """
        status_names = {
            OUT_OF_OFFICE: "OUT_OF_OFFICE",
            WORK_FROM_HOME: "WORK_FROM_HOME",
            GOING_TO_EVENT: "GOING_TO_EVENT",
            FOCUS_TIME: "FOCUS_TIME",
            AVAILABLE: "AVAILABLE",
            IN_MEETING: "IN_MEETING"
        }
        
        # Variables to track potential statuses
        found_statuses = []
        
        for event in events:
            # Skip cancelled events
            if event.get('status') == 'cancelled':
                continue
            
            # Get event times
            start = event.get('start', {})
            end = event.get('end', {})
            
            # Check if it's an all-day event
            is_all_day = 'date' in start
            
            if is_all_day:
                # All-day events apply to the whole day
                event_start = datetime.datetime.strptime(start['date'], '%Y-%m-%d')
                event_end = datetime.datetime.strptime(end['date'], '%Y-%m-%d')
                # For comparison with all-day events, get today's date (without time)
                today = datetime.datetime(now.year, now.month, now.day)
            else:
                # Timed events
                start_str = start.get('dateTime', '')
                end_str = end.get('dateTime', '')
                if not start_str or not end_str:
                    continue
                    
                # Parse datetime (handle timezone)
                event_start = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                event_end = datetime.datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                
                # Make now timezone-aware if event times are
                if event_start.tzinfo is not None:
                    now_aware = now.replace(tzinfo=datetime.timezone.utc)
                else:
                    now_aware = now
            
            # Get event type for special event checks
            event_type = event.get('eventType', 'default')
            transparency = event.get('transparency', 'opaque')  # Default is opaque (busy)
            
            # For timed events, check time-based conditions
            if not is_all_day:
                # Check for special event types FIRST (before generic busy check)
                # This prevents special events from being classified as generic IN_MEETING
                
                # Check OUT_OF_OFFICE (currently in an out of office event)
                if event_type == 'outOfOffice' and event_start <= now_aware <= event_end:
                    found_statuses.append((OUT_OF_OFFICE, event))
                    self.logger.debug(f"Found OUT_OF_OFFICE event: {event.get('summary', 'No title')}")
                # Check FOCUS_TIME (currently in focus time)
                elif event_type == 'focusTime' and event_start <= now_aware <= event_end:
                    found_statuses.append((FOCUS_TIME, event))
                    self.logger.debug(f"Found FOCUS_TIME event: {event.get('summary', 'No title')}")
                # Check WORK_FROM_HOME (currently working from home)
                elif event.get('workingLocationProperties', {}).get('type') == 'homeOffice' and event_start <= now_aware <= event_end:
                    found_statuses.append((WORK_FROM_HOME, event))
                    self.logger.debug(f"Found WORK_FROM_HOME event: {event.get('summary', 'No title')}")
                # Check IN_MEETING (currently in a busy event, but not a special type)
                elif transparency == 'opaque' and event_start <= now_aware <= event_end:
                    found_statuses.append((IN_MEETING, event))
                    self.logger.debug(f"Found IN_MEETING event: {event.get('summary', 'No title')}")
                
                # Check GOING_TO_EVENT (busy event in next 5 minutes, not a special type)
                time_until_event = (event_start - now_aware).total_seconds()
                special_types = ['focusTime', 'outOfOffice']
                has_working_location = bool(event.get('workingLocationProperties'))
                if event_type not in special_types and not has_working_location and transparency == 'opaque' and 0 < time_until_event <= 300:  # 300 seconds = 5 minutes
                    found_statuses.append((GOING_TO_EVENT, event))
                    self.logger.debug(f"Found GOING_TO_EVENT event: {event.get('summary', 'No title')}")
            
            # Check OUT_OF_OFFICE for all-day events (timed events handled above)
            # For all-day events, end date is exclusive (event from 11/10 to 11/11 only applies on 11/10)
            if is_all_day and event_type == 'outOfOffice':
                if event_start <= today < event_end:
                    found_statuses.append((OUT_OF_OFFICE, event))
                    self.logger.debug(f"Found OUT_OF_OFFICE all-day event: {event.get('summary', 'No title')}")
            
            # Check WORK_FROM_HOME for all-day events (timed events handled above)
            if is_all_day:
                working_location = event.get('workingLocationProperties', {})
                if working_location:
                    location_type = working_location.get('type', '')
                    if location_type == 'homeOffice' and event_start <= today < event_end:
                        found_statuses.append((WORK_FROM_HOME, event))
                        self.logger.debug(f"Found WORK_FROM_HOME all-day event: {event.get('summary', 'No title')}")
        
        # Return the highest precedence status found
        if found_statuses:
            # Sort by precedence (lower precedence number = higher priority)
            found_statuses.sort(key=lambda x: STATUS_PRECEDENCE[x[0]])
            status_code, event = found_statuses[0]
            
            return {
                "status": status_code,
                "status_name": status_names[status_code],
                "event_summary": event.get('summary', 'No title'),
                "event_start": event.get('start', {}),
                "event_end": event.get('end', {}),
                "event_type": event.get('eventType', 'default')
            }
        
        # Default: AVAILABLE
        return {
            "status": AVAILABLE,
            "status_name": status_names[AVAILABLE],
            "message": "No events found matching criteria"
        }

    async def _reset_wheel(self) -> None:
        """Perform the initial wheel reset by rotating 1 full revolution.
        
        This establishes a known position (OUT_OF_OFFICE) after reconfiguration.
        """
        if self.reverse_motor:
            revolutions = -1
        else:
            revolutions = 1
        
        self.logger.info("Resetting wheel position - performing 1 full revolution at 15 RPM")
        
        # Perform 1 full revolution to reset the wheel
        await self.motor.go_for(rpm=15, revolutions=revolutions)
        
        # After reset, set position to OUT_OF_OFFICE
        self.current_position = OUT_OF_OFFICE
        self.needs_reset = False
        
        self.logger.info("Wheel reset complete - now at OUT_OF_OFFICE position")
    
    async def _move_to_position(self, target_position: int, context: dict = None) -> Mapping[str, ValueTypes]:
        """Move the wheel to a specific position.
        
        Args:
            target_position: Target position (0-5)
            context: Optional context dictionary to include in response (e.g., calendar status)
            
        Returns:
            dict: Movement information including old/new positions and revolutions moved
        """
        try:
            # Check if already at target position
            if target_position == self.current_position:
                self.logger.info(f"Already at position {target_position} - no movement needed")
                result = {
                    "motor_action": "none",
                    "current_position": self.current_position,
                    "revolutions_moved": 0
                }
                if context:
                    result.update(context)
                return result
            
            # Calculate the offset in 1/6th rotations
            # Each position is 1/6 of a full rotation (60 degrees)
            position_offset = target_position - self.current_position
            revolutions = position_offset / 6.0
            if self.reverse_motor:
                revolutions = -revolutions
            
            self.logger.info(f"Moving from position {self.current_position} to {target_position}")
            self.logger.info(f"Movement: {position_offset} positions ({position_offset}/6 = {revolutions} revolutions)")
            
            # Move the motor
            await self.motor.go_for(rpm=15, revolutions=revolutions)
            
            # Update current position
            old_position = self.current_position
            self.current_position = target_position
            
            self.logger.info(f"Wheel movement complete - now at position {self.current_position}")
            
            # Return movement info
            result = {
                "motor_action": "moved",
                "old_position": old_position,
                "current_position": self.current_position,
                "revolutions_moved": revolutions
            }
            if context:
                result.update(context)
            return result
            
        except Exception as e:
            self.logger.error(f"Error moving to position {target_position}: {e}")
            raise

    async def turn_wheel(self) -> Mapping[str, ValueTypes]:
        """Turn the wheel to the appropriate position based on calendar status.
        
        This method:
        1. Performs a reset (1 full revolution) if needed after reconfiguration
        2. Gets the current calendar status
        3. Moves the motor to the appropriate position
        4. Returns the calendar status and motor movement info
        
        Returns:
            dict: Status information including calendar status and motor movement
        """
        try:
            # Step 1: Reset wheel if needed (after reconfiguration)
            if self.needs_reset:
                await self._reset_wheel()
            
            # Step 2: Get calendar status
            calendar_status = await self.get_calendar_status()
            
            # Check if there was an error getting calendar status
            if "error" in calendar_status:
                return {
                    "error": calendar_status["error"],
                    "current_position": self.current_position
                }
            
            # Step 3: Determine target position from calendar status
            target_position = calendar_status.get("status", AVAILABLE)
            status_name = calendar_status.get("status_name", "AVAILABLE")
            
            self.logger.info(f"Calendar status: {status_name} (position {target_position})")
            
            # Step 4: Move to target position
            return await self._move_to_position(target_position, context=calendar_status)
            
        except Exception as e:
            self.logger.error(f"Error in turn_wheel: {e}")
            return {
                "error": f"Motor control error: {e}",
                "current_position": getattr(self, 'current_position', None)
            }
    
    async def test_wheel(self, status_name: str = None) -> Mapping[str, ValueTypes]:
        """Manually move the wheel to a specific position for testing.
        
        This command bypasses calendar checking and moves directly to the specified position.
        Useful for testing motor control and verifying wheel positions.
        
        Args:
            status_name: Name of the status position to move to (e.g., "IN_MEETING", "AVAILABLE")
            
        Returns:
            dict: Movement information including target position and revolutions moved
        """
        # Status name to position mapping
        status_map = {
            "IN_MEETING": IN_MEETING,
            "GOING_TO_EVENT": GOING_TO_EVENT,
            "FOCUS_TIME": FOCUS_TIME,
            "OUT_OF_OFFICE": OUT_OF_OFFICE,
            "WORK_FROM_HOME": WORK_FROM_HOME,
            "AVAILABLE": AVAILABLE
        }
        
        try:
            # Reset wheel if needed
            if self.needs_reset:
                await self._reset_wheel()
            
            # Validate and get target position
            if not status_name or status_name not in status_map:
                return {
                    "error": f"Invalid status name. Must be one of: {', '.join(status_map.keys())}",
                    "current_position": self.current_position,
                    "valid_statuses": list(status_map.keys())
                }
            
            target_position = status_map[status_name]
            
            self.logger.info(f"Test mode: Moving to {status_name} (position {target_position})")
            
            # Move to target position
            result = await self._move_to_position(target_position, context={
                "test_mode": True,
                "target_status": status_name,
                "target_position": target_position
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in test_wheel: {e}")
            return {
                "error": f"Test wheel error: {e}",
                "current_position": getattr(self, 'current_position', None)
            }
    