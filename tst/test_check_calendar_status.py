#!/usr/bin/env python3
"""
Comprehensive unit tests for _check_calendar_status method.

Tests all event types, timing scenarios, and precedence rules.

Usage:
    python -m pytest tst/test_check_calendar_status.py -v
    or
    python tst/test_check_calendar_status.py
"""

import unittest
from datetime import datetime, timezone
import sys
import os

# Import the service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from models.google_calender_service import (
    GoogleCalenderService,
    OUT_OF_OFFICE,
    WORK_FROM_HOME,
    GOING_TO_EVENT,
    FOCUS_TIME,
    AVAILABLE,
    IN_MEETING
)


class MockLogger:
    """Mock logger for testing."""
    def __init__(self):
        self.debug_messages = []
        self.info_messages = []
        self.error_messages = []
    
    def debug(self, msg):
        self.debug_messages.append(msg)
        print(f"[DEBUG] {msg}")
    
    def info(self, msg):
        self.info_messages.append(msg)
        print(f"[INFO] {msg}")
    
    def error(self, msg):
        self.error_messages.append(msg)
        print(f"[ERROR] {msg}")


class TestCheckCalendarStatus(unittest.TestCase):
    """Test cases for _check_calendar_status method."""
    
    def setUp(self):
        """Set up test instance."""
        self.service = GoogleCalenderService.__new__(GoogleCalenderService)
        self.service.logger = MockLogger()
        
        # Use a fixed "now" time for consistent testing: 2025-11-09 10:00:00 UTC
        self.now = datetime(2025, 11, 9, 10, 0, 0, tzinfo=timezone.utc)
    
    def test_available_no_events(self):
        """Test AVAILABLE status when no events exist."""
        events = []
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], AVAILABLE)
        self.assertEqual(result['status_name'], 'AVAILABLE')
        self.assertIn('message', result)
    
    def test_in_meeting_current(self):
        """Test IN_MEETING status for current busy event."""
        events = [{
            'summary': 'Team Meeting',
            'start': {'dateTime': '2025-11-09T09:30:00Z'},
            'end': {'dateTime': '2025-11-09T10:30:00Z'},
            'transparency': 'opaque',
            'eventType': 'default'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], IN_MEETING)
        self.assertEqual(result['status_name'], 'IN_MEETING')
        self.assertEqual(result['event_summary'], 'Team Meeting')
    
    def test_in_meeting_not_current(self):
        """Test that past meeting doesn't trigger IN_MEETING."""
        events = [{
            'summary': 'Past Meeting',
            'start': {'dateTime': '2025-11-09T08:00:00Z'},
            'end': {'dateTime': '2025-11-09T09:00:00Z'},
            'transparency': 'opaque',
            'eventType': 'default'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], AVAILABLE)
    
    def test_focus_time_current(self):
        """Test FOCUS_TIME status for current focus time event."""
        events = [{
            'summary': 'Focus Time',
            'start': {'dateTime': '2025-11-09T09:00:00Z'},
            'end': {'dateTime': '2025-11-09T11:00:00Z'},
            'eventType': 'focusTime',
            'transparency': 'opaque'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], FOCUS_TIME)
        self.assertEqual(result['status_name'], 'FOCUS_TIME')
        self.assertEqual(result['event_summary'], 'Focus Time')
    
    def test_focus_time_not_current(self):
        """Test that future focus time doesn't trigger FOCUS_TIME."""
        events = [{
            'summary': 'Focus Time',
            'start': {'dateTime': '2025-11-09T14:00:00Z'},
            'end': {'dateTime': '2025-11-09T16:00:00Z'},
            'eventType': 'focusTime',
            'transparency': 'opaque'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], AVAILABLE)
    
    def test_out_of_office_timed_current(self):
        """Test OUT_OF_OFFICE for current timed OOO event."""
        events = [{
            'summary': 'OOO',
            'start': {'dateTime': '2025-11-09T00:00:00-05:00'},
            'end': {'dateTime': '2025-11-10T00:00:00-05:00'},
            'eventType': 'outOfOffice',
            'transparency': 'opaque'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], OUT_OF_OFFICE)
        self.assertEqual(result['status_name'], 'OUT_OF_OFFICE')
        self.assertEqual(result['event_summary'], 'OOO')
    
    def test_out_of_office_all_day_today(self):
        """Test OUT_OF_OFFICE for all-day event on current day."""
        events = [{
            'summary': 'OOO All Day',
            'start': {'date': '2025-11-09'},
            'end': {'date': '2025-11-10'},  # End is exclusive
            'eventType': 'outOfOffice'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], OUT_OF_OFFICE)
        self.assertEqual(result['status_name'], 'OUT_OF_OFFICE')
        self.assertEqual(result['event_summary'], 'OOO All Day')
    
    def test_out_of_office_all_day_tomorrow(self):
        """Test that tomorrow's all-day OOO doesn't trigger today."""
        events = [{
            'summary': 'OOO Tomorrow',
            'start': {'date': '2025-11-10'},
            'end': {'date': '2025-11-11'},
            'eventType': 'outOfOffice'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], AVAILABLE)
        self.assertNotEqual(result['status_name'], 'OUT_OF_OFFICE')
    
    def test_out_of_office_all_day_yesterday(self):
        """Test that yesterday's all-day OOO doesn't trigger today."""
        events = [{
            'summary': 'OOO Yesterday',
            'start': {'date': '2025-11-08'},
            'end': {'date': '2025-11-09'},  # End is exclusive, so doesn't include today
            'eventType': 'outOfOffice'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], AVAILABLE)
    
    def test_work_from_home_timed_current(self):
        """Test WORK_FROM_HOME for current timed WFH event."""
        events = [{
            'summary': 'WFH',
            'start': {'dateTime': '2025-11-09T08:00:00Z'},
            'end': {'dateTime': '2025-11-09T17:00:00Z'},
            'eventType': 'workingLocation',
            'workingLocationProperties': {'type': 'homeOffice'}
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], WORK_FROM_HOME)
        self.assertEqual(result['status_name'], 'WORK_FROM_HOME')
    
    def test_work_from_home_all_day_today(self):
        """Test WORK_FROM_HOME for all-day event on current day."""
        events = [{
            'summary': 'Home',
            'start': {'date': '2025-11-09'},
            'end': {'date': '2025-11-10'},
            'eventType': 'workingLocation',
            'workingLocationProperties': {'type': 'homeOffice'}
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], WORK_FROM_HOME)
        self.assertEqual(result['status_name'], 'WORK_FROM_HOME')
    
    def test_work_from_home_all_day_tomorrow(self):
        """Test that tomorrow's all-day WFH doesn't trigger today."""
        events = [{
            'summary': 'Home',
            'start': {'date': '2025-11-10'},
            'end': {'date': '2025-11-11'},
            'eventType': 'workingLocation',
            'workingLocationProperties': {'type': 'homeOffice'}
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], AVAILABLE)
        self.assertNotEqual(result['status_name'], 'WORK_FROM_HOME')
    
    def test_work_from_home_date_format_validation(self):
        """Test that date format with yyyy-mm-dd is correctly parsed and validated.
        
        This test ensures that when checking an event scheduled for tomorrow
        (2025-11-10 to 2025-11-11) while today is 2025-11-09, the event is
        correctly identified as not applicable to today.
        """
        # Current time: 2025-11-09 10:00:00 UTC
        # Event: 2025-11-10 to 2025-11-11 (tomorrow)
        events = [{
            'summary': 'Home',
            'start': {'date': '2025-11-10'},
            'end': {'date': '2025-11-11'},
            'eventType': 'workingLocation',
            'workingLocationProperties': {'type': 'homeOffice'},
            'status': 'confirmed'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        # Should return AVAILABLE since the event is tomorrow, not today
        self.assertEqual(result['status'], AVAILABLE)
        self.assertEqual(result['status_name'], 'AVAILABLE')
        self.assertIn('message', result)
        
        # Now test when we advance time to tomorrow (2025-11-10)
        tomorrow = datetime(2025, 11, 10, 10, 0, 0, tzinfo=timezone.utc)
        result_tomorrow = self.service._check_calendar_status(events, tomorrow)
        
        # Should now return WORK_FROM_HOME since we're on the event date
        self.assertEqual(result_tomorrow['status'], WORK_FROM_HOME)
        self.assertEqual(result_tomorrow['status_name'], 'WORK_FROM_HOME')
        self.assertEqual(result_tomorrow['event_summary'], 'Home')
        self.assertEqual(result_tomorrow['event_type'], 'workingLocation')
        self.assertEqual(result_tomorrow['event_start'], {'date': '2025-11-10'})
        self.assertEqual(result_tomorrow['event_end'], {'date': '2025-11-11'})
    
    def test_work_from_home_all_day_yesterday(self):
        """Test that yesterday's all-day WFH doesn't trigger today."""
        events = [{
            'summary': 'Home',
            'start': {'date': '2025-11-08'},
            'end': {'date': '2025-11-09'},  # Exclusive end
            'eventType': 'workingLocation',
            'workingLocationProperties': {'type': 'homeOffice'}
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], AVAILABLE)
    
    def test_going_to_event_5_minutes(self):
        """Test GOING_TO_EVENT for event starting in 5 minutes."""
        events = [{
            'summary': 'Upcoming Meeting',
            'start': {'dateTime': '2025-11-09T10:05:00Z'},  # 5 minutes from now
            'end': {'dateTime': '2025-11-09T11:00:00Z'},
            'transparency': 'opaque',
            'eventType': 'default'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], GOING_TO_EVENT)
        self.assertEqual(result['status_name'], 'GOING_TO_EVENT')
    
    def test_going_to_event_1_minute(self):
        """Test GOING_TO_EVENT for event starting in 1 minute."""
        events = [{
            'summary': 'Very Soon',
            'start': {'dateTime': '2025-11-09T10:01:00Z'},
            'end': {'dateTime': '2025-11-09T11:00:00Z'},
            'transparency': 'opaque',
            'eventType': 'default'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], GOING_TO_EVENT)
    
    def test_going_to_event_6_minutes_not_triggered(self):
        """Test that event in 6 minutes doesn't trigger GOING_TO_EVENT."""
        events = [{
            'summary': 'Later Meeting',
            'start': {'dateTime': '2025-11-09T10:06:00Z'},  # 6 minutes from now
            'end': {'dateTime': '2025-11-09T11:00:00Z'},
            'transparency': 'opaque',
            'eventType': 'default'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], AVAILABLE)
    
    def test_going_to_event_not_for_focus_time(self):
        """Test that upcoming focus time doesn't trigger GOING_TO_EVENT."""
        events = [{
            'summary': 'Focus Time Soon',
            'start': {'dateTime': '2025-11-09T10:03:00Z'},
            'end': {'dateTime': '2025-11-09T12:00:00Z'},
            'eventType': 'focusTime',
            'transparency': 'opaque'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        # Should be AVAILABLE, not GOING_TO_EVENT (focus time is excluded)
        self.assertEqual(result['status'], AVAILABLE)
    
    def test_going_to_event_not_for_ooo(self):
        """Test that upcoming OOO doesn't trigger GOING_TO_EVENT."""
        events = [{
            'summary': 'OOO Soon',
            'start': {'dateTime': '2025-11-09T10:03:00Z'},
            'end': {'dateTime': '2025-11-09T17:00:00Z'},
            'eventType': 'outOfOffice',
            'transparency': 'opaque'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        # Should be AVAILABLE, not GOING_TO_EVENT (OOO is excluded)
        self.assertEqual(result['status'], AVAILABLE)
    
    def test_precedence_in_meeting_over_work_from_home(self):
        """Test that IN_MEETING takes precedence over WORK_FROM_HOME by priority."""
        events = [
            {
                'summary': 'Meeting',
                'start': {'dateTime': '2025-11-09T09:30:00Z'},
                'end': {'dateTime': '2025-11-09T10:30:00Z'},
                'transparency': 'opaque',
                'eventType': 'default'
            },
            {
                'summary': 'WFH All Day',
                'start': {'date': '2025-11-09'},
                'end': {'date': '2025-11-10'},
                'eventType': 'workingLocation',
                'workingLocationProperties': {'type': 'homeOffice'}
            }
        ]
        result = self.service._check_calendar_status(events, self.now)
        
        # IN_MEETING (position 0) has higher priority than WORK_FROM_HOME (position 4)
        self.assertEqual(result['status'], IN_MEETING)
        self.assertEqual(result['event_summary'], 'Meeting')
    
    def test_precedence_out_of_office_over_in_meeting(self):
        """Test that OUT_OF_OFFICE takes precedence over IN_MEETING by priority.
        
        When there's a regular meeting during an OOO period, OUT_OF_OFFICE wins because
        it has the highest priority (even though IN_MEETING is position 0 and OOO is position 5).
        """
        events = [
            {
                'summary': 'OOO Full Day',
                'start': {'dateTime': '2025-11-09T00:00:00-05:00'},
                'end': {'dateTime': '2025-11-10T00:00:00-05:00'},
                'eventType': 'outOfOffice',
                'transparency': 'opaque'
            },
            {
                'summary': 'Regular Meeting',
                'start': {'dateTime': '2025-11-09T09:30:00Z'},
                'end': {'dateTime': '2025-11-09T10:30:00Z'},
                'transparency': 'opaque',
                'eventType': 'default'
            }
        ]
        result = self.service._check_calendar_status(events, self.now)
        
        # OUT_OF_OFFICE (position 5) has higher priority than IN_MEETING (position 0)
        self.assertEqual(result['status'], OUT_OF_OFFICE)
        self.assertEqual(result['event_summary'], 'OOO Full Day')
    
    def test_precedence_in_meeting_over_focus_time(self):
        """Test that IN_MEETING takes precedence over FOCUS_TIME by priority.
        
        When a regular meeting overlaps with a focus time event, IN_MEETING should win
        because it has higher priority (priority 1 vs FOCUS_TIME priority 2).
        """
        events = [
            {
                'summary': 'Focus Time',
                'start': {'dateTime': '2025-11-09T09:00:00Z'},
                'end': {'dateTime': '2025-11-09T11:00:00Z'},
                'eventType': 'focusTime',
                'transparency': 'opaque'
            },
            {
                'summary': 'Overlapping Meeting',
                'start': {'dateTime': '2025-11-09T09:30:00Z'},
                'end': {'dateTime': '2025-11-09T10:30:00Z'},
                'transparency': 'opaque',
                'eventType': 'default'
            }
        ]
        result = self.service._check_calendar_status(events, self.now)
        
        # IN_MEETING (position 0) has higher priority than FOCUS_TIME (position 2)
        self.assertEqual(result['status'], IN_MEETING)
        self.assertEqual(result['event_summary'], 'Overlapping Meeting')
    
    def test_transparent_event_not_busy(self):
        """Test that transparent (free) events don't trigger IN_MEETING."""
        events = [{
            'summary': 'Personal Time',
            'start': {'dateTime': '2025-11-09T09:30:00Z'},
            'end': {'dateTime': '2025-11-09T10:30:00Z'},
            'transparency': 'transparent',
            'eventType': 'default'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], AVAILABLE)
    
    def test_cancelled_event_ignored(self):
        """Test that cancelled events are ignored."""
        events = [{
            'summary': 'Cancelled Meeting',
            'start': {'dateTime': '2025-11-09T09:30:00Z'},
            'end': {'dateTime': '2025-11-09T10:30:00Z'},
            'transparency': 'opaque',
            'eventType': 'default',
            'status': 'cancelled'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], AVAILABLE)
    
    def test_multi_day_out_of_office_includes_today(self):
        """Test multi-day OOO that includes today."""
        events = [{
            'summary': 'Vacation',
            'start': {'date': '2025-11-08'},
            'end': {'date': '2025-11-12'},  # Nov 8-11 inclusive
            'eventType': 'outOfOffice'
        }]
        result = self.service._check_calendar_status(events, self.now)
        
        self.assertEqual(result['status'], OUT_OF_OFFICE)
        self.assertEqual(result['event_summary'], 'Vacation')
    
    def test_all_day_event_boundary_start(self):
        """Test all-day event on its start date."""
        # Testing at midnight of start date
        now_midnight = datetime(2025, 11, 9, 0, 0, 0, tzinfo=timezone.utc)
        
        events = [{
            'summary': 'All Day Event',
            'start': {'date': '2025-11-09'},
            'end': {'date': '2025-11-10'},
            'eventType': 'outOfOffice'
        }]
        result = self.service._check_calendar_status(events, now_midnight)
        
        self.assertEqual(result['status'], OUT_OF_OFFICE)
    
    def test_all_day_event_boundary_end(self):
        """Test all-day event at its end boundary (exclusive)."""
        # Testing at midnight of end date (should not include)
        now_next_day = datetime(2025, 11, 10, 0, 0, 0, tzinfo=timezone.utc)
        
        events = [{
            'summary': 'All Day Event',
            'start': {'date': '2025-11-09'},
            'end': {'date': '2025-11-10'},  # Exclusive
            'eventType': 'outOfOffice'
        }]
        result = self.service._check_calendar_status(events, now_next_day)
        
        self.assertEqual(result['status'], AVAILABLE)
    
    def test_complex_scenario_all_types(self):
        """Test complex scenario with multiple event types."""
        events = [
            {
                'summary': 'WFH',
                'start': {'date': '2025-11-09'},
                'end': {'date': '2025-11-10'},
                'eventType': 'workingLocation',
                'workingLocationProperties': {'type': 'homeOffice'}
            },
            {
                'summary': 'Current Meeting',
                'start': {'dateTime': '2025-11-09T09:30:00Z'},
                'end': {'dateTime': '2025-11-09T10:30:00Z'},
                'transparency': 'opaque',
                'eventType': 'default'
            },
            {
                'summary': 'Upcoming Event',
                'start': {'dateTime': '2025-11-09T11:00:00Z'},
                'end': {'dateTime': '2025-11-09T12:00:00Z'},
                'transparency': 'opaque',
                'eventType': 'default'
            }
        ]
        result = self.service._check_calendar_status(events, self.now)
        
        # IN_MEETING (0) should win over WORK_FROM_HOME (4)
        self.assertEqual(result['status'], IN_MEETING)
        self.assertEqual(result['event_summary'], 'Current Meeting')


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestCheckCalendarStatus)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

