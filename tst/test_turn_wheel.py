#!/usr/bin/env python3
"""
Test script for the turn_wheel command.

This script can be used to test the turn_wheel logic without running the full Viam module.
It simulates the module environment and calls the turn_wheel functionality.

Usage:
    python test_turn_wheel.py

Prerequisites:
    - Run get_token.py first to generate credentials
    - Set VIAM_MODULE_DATA environment variable to the directory containing token.json
    - Or the script will look for token.json in the current directory
"""

import os
import sys
import json
from datetime import datetime

# Set up the module data directory for testing
if not os.environ.get('VIAM_MODULE_DATA'):
    # Default to current directory for testing
    os.environ['VIAM_MODULE_DATA'] = os.getcwd()
    print(f"VIAM_MODULE_DATA not set, using current directory: {os.getcwd()}")

# Import the service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from models.google_calender_service import (
    GoogleCalenderService,
    OUT_OF_OFFICE,
    WORK_FROM_HOME,
    GOING_TO_EVENT,
    FOCUS_TIME,
    AVAILABLE,
    IN_MEETING
)

import asyncio


async def test_turn_wheel():
    """Test the turn_wheel command."""
    print("=" * 70)
    print("Testing turn_wheel command")
    print("=" * 70)
    print()
    
    # Check if token.json exists
    token_path = os.path.join(os.environ['VIAM_MODULE_DATA'], 'token.json')
    if not os.path.exists(token_path):
        print(f"❌ ERROR: token.json not found at {token_path}")
        print()
        print("Please run get_token.py first to generate credentials:")
        print("  python get_token.py")
        print()
        print("Or set VIAM_MODULE_DATA to the directory containing token.json:")
        print("  export VIAM_MODULE_DATA=/path/to/your/data/directory")
        return
    
    print(f"✓ Found token.json at {token_path}")
    print()
    
    # Create a mock service instance
    # Note: We can't fully instantiate the service without Viam infrastructure,
    # so we'll call the method directly
    service = GoogleCalenderService.__new__(GoogleCalenderService)
    
    # Mock the logger
    class MockLogger:
        def debug(self, msg):
            print(f"[DEBUG] {msg}")
        
        def info(self, msg):
            print(f"[INFO] {msg}")
        
        def error(self, msg):
            print(f"[ERROR] {msg}")
    
    service.logger = MockLogger()
    
    print("Fetching calendar events and detecting status...")
    print()
    
    try:
        # Call turn_wheel
        result = await service.turn_wheel()
        
        print("=" * 70)
        print("RESULT")
        print("=" * 70)
        print(json.dumps(result, indent=2, default=str))
        print()
        
        if "error" not in result:
            status_code = result.get("status")
            status_name = result.get("status_name")
            
            status_descriptions = {
                OUT_OF_OFFICE: "You are out of office",
                IN_MEETING: "You are currently in a meeting",
                FOCUS_TIME: "You are in focus time",
                WORK_FROM_HOME: "You are working from home",
                GOING_TO_EVENT: "You have an event starting soon",
                AVAILABLE: "You are available"
            }
            
            print(f"Status: {status_name} ({status_code})")
            print(f"Meaning: {status_descriptions.get(status_code, 'Unknown')}")
            
            if "event_summary" in result:
                print(f"Event: {result['event_summary']}")
        
        print()
        print("✓ Test completed successfully")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


async def main():
    await test_turn_wheel()


if __name__ == '__main__':
    asyncio.run(main())

