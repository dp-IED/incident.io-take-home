#!/usr/bin/env python3
"""
Simple example demonstrating the on-call scheduling system.
This recreates the example from the README.
"""

from datetime import datetime, timezone
import sys
import os

# Add parent directory to path so we can import utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils import Schedule, Override, render_schedule
import json


def main():
    # Alice, Bob, Charlie rotating weekly
    # Starting Friday Nov 7, 2025 at 5pm
    schedule = Schedule(
        users=["alice", "bob", "charlie"],
        handover_start_at=datetime(2025, 11, 7, 17, 0, tzinfo=timezone.utc),
        handover_interval_days=7
    )
    
    # Charlie covers 5pm-10pm on Monday 10th November 2025
    overrides = [
        Override(
            user="charlie",
            start_at=datetime(2025, 11, 10, 17, 0, tzinfo=timezone.utc),
            end_at=datetime(2025, 11, 10, 22, 0, tzinfo=timezone.utc)
        )
    ]
    
    # Generate schedule for 2 weeks from 7th November 2025 to 21st November 2025
    from_time = datetime(2025, 11, 7, 17, 0, tzinfo=timezone.utc)
    until_time = datetime(2025, 11, 21, 17, 0, tzinfo=timezone.utc)
    
    print(f"Generating schedule from {from_time.strftime('%Y-%m-%d')} to {until_time.strftime('%Y-%m-%d')}...")
    
    entries = render_schedule(schedule, overrides, from_time, until_time)
    
    output = []
    for entry in entries:
        output.append({
            'user': entry['user'],
            'start_at': entry['start_at'].strftime('%Y-%m-%dT%H:%M:%SZ'),
            'end_at': entry['end_at'].strftime('%Y-%m-%dT%H:%M:%SZ')
        })
    
    print(json.dumps(output, indent=2))
    
    for entry in entries:
        start_str = entry['start_at'].strftime('%a %b %d, %I:%M %p')
        end_str = entry['end_at'].strftime('%a %b %d, %I:%M %p')
        duration = entry['end_at'] - entry['start_at']
        
        # Calculate hours
        hours = duration.total_seconds() / 3600
        if hours < 24:
            duration_str = f"{hours:.1f} hours"
        else:
            days = hours / 24
            duration_str = f"{days:.1f} days"
        
        print(f"{entry['user']:8} | {start_str} → {end_str} ({duration_str})")


if __name__ == '__main__':
    main()

