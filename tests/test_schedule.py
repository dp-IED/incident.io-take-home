"""
Tests for the schedule rendering system.

- Basic schedule generation
- Schedule with overrides
- Overlapping overrides
- Chained overrides
- Edge cases (truncation, merging)
- Invalid inputs
"""

import pytest
from datetime import datetime, timezone
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import (
    Schedule,
    Override,
    generate_base_schedule,
    apply_overrides,
    render_schedule,
    truncate_to_window,
    merge_consecutive_entries
)


class TestBasicScheduleGeneration:
    """Test basic schedule generation without overrides."""
    
    def test_simple_rotation(self):
        """Test basic user rotation."""
        schedule = Schedule(
            users=["alice", "bob", "charlie"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        entries = generate_base_schedule(schedule, datetime(2025, 11, 28, 17, 0, 0, tzinfo=timezone.utc))
        
        assert len(entries) == 3
        assert entries[0]['user'] == 'alice'
        assert entries[1]['user'] == 'bob'
        assert entries[2]['user'] == 'charlie'
    
    def test_rotation_wraps_around(self):
        """Test that rotation cycles back to first user."""
        schedule = Schedule(
            users=["alice", "bob"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        entries = generate_base_schedule(schedule, datetime(2025, 12, 5, 17, 0, 0, tzinfo=timezone.utc))
        
        assert len(entries) == 4
        assert entries[0]['user'] == 'alice'
        assert entries[1]['user'] == 'bob'
        assert entries[2]['user'] == 'alice'  # Wraps around
        assert entries[3]['user'] == 'bob'
    
    def test_single_user_schedule(self):
        """Test schedule with only one user."""
        schedule = Schedule(
            users=["alice"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        entries = generate_base_schedule(schedule, datetime(2025, 11, 28, 17, 0, 0, tzinfo=timezone.utc))
        
        assert len(entries) == 3
        assert all(entry['user'] == 'alice' for entry in entries)
    
    def test_daily_handover(self):
        """Test schedule with daily handovers."""
        schedule = Schedule(
            users=["alice", "bob"],
            handover_start_at=datetime(2025, 11, 7, 9, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=1
        )
        
        entries = generate_base_schedule(schedule, datetime(2025, 11, 10, 9, 0, 0, tzinfo=timezone.utc))
        
        assert len(entries) == 3
        assert entries[0]['user'] == 'alice'
        assert entries[1]['user'] == 'bob'
        assert entries[2]['user'] == 'alice'


class TestOverrides:
    """Test override functionality."""
    
    def test_single_override(self):
        """Test applying a single override to a shift."""
        schedule = Schedule(
            users=["alice", "bob", "charlie"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        base_entries = generate_base_schedule(schedule, datetime(2025, 11, 21, 17, 0, 0, tzinfo=timezone.utc))
        
        overrides = [
            Override(
                user="charlie",
                start_at=datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 11, 10, 22, 0, 0, tzinfo=timezone.utc)
            )
        ]
        
        entries = apply_overrides(base_entries, overrides)
        
        # Should split alice's shift into 3 parts
        alice_entries = [e for e in entries if e['user'] == 'alice']
        charlie_override = [e for e in entries if e['user'] == 'charlie' and 
                          e['start_at'] == datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc)]
        
        assert len(alice_entries) == 2  # Before and after override
        assert len(charlie_override) == 1
    
    def test_multiple_non_overlapping_overrides(self):
        """Test multiple overrides that don't overlap."""
        schedule = Schedule(
            users=["alice", "bob"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        base_entries = generate_base_schedule(schedule, datetime(2025, 11, 21, 17, 0, 0, tzinfo=timezone.utc))
        
        overrides = [
            Override(
                user="charlie",
                start_at=datetime(2025, 11, 8, 9, 0, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 11, 8, 17, 0, 0, tzinfo=timezone.utc)
            ),
            Override(
                user="charlie",
                start_at=datetime(2025, 11, 15, 9, 0, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 11, 15, 17, 0, 0, tzinfo=timezone.utc)
            )
        ]
        
        entries = apply_overrides(base_entries, overrides)
        
        charlie_entries = [e for e in entries if e['user'] == 'charlie']
        assert len(charlie_entries) == 2
    
    def test_override_at_shift_boundary(self):
        """Test override that starts exactly at a shift boundary."""
        schedule = Schedule(
            users=["alice", "bob"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        base_entries = generate_base_schedule(schedule, datetime(2025, 11, 21, 17, 0, 0, tzinfo=timezone.utc))
        
        overrides = [
            Override(
                user="charlie",
                start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 11, 8, 17, 0, 0, tzinfo=timezone.utc)
            )
        ]
        
        entries = apply_overrides(base_entries, overrides)
        
        # First entry should be charlie's override
        assert entries[0]['user'] == 'charlie'
        assert entries[0]['start_at'] == datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)
    
    def test_override_spanning_entire_shift(self):
        """Test override that covers an entire shift."""
        schedule = Schedule(
            users=["alice", "bob"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        base_entries = generate_base_schedule(schedule, datetime(2025, 11, 21, 17, 0, 0, tzinfo=timezone.utc))
        
        overrides = [
            Override(
                user="charlie",
                start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
            )
        ]
        
        entries = apply_overrides(base_entries, overrides)
        
        # Alice's first shift should be completely replaced
        alice_first_shift = [e for e in entries if e['user'] == 'alice' and 
                            e['start_at'] == datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)]
        assert len(alice_first_shift) == 0
        
        # Charlie should have the entire first week
        charlie_entries = [e for e in entries if e['user'] == 'charlie']
        assert len(charlie_entries) == 1
        assert charlie_entries[0]['start_at'] == datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)
        assert charlie_entries[0]['end_at'] == datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)


class TestChainedOverrides:
    """Test chained/consecutive overrides."""
    
    def test_back_to_back_overrides(self):
        """Test two overrides that are consecutive (end of one = start of next)."""
        schedule = Schedule(
            users=["alice"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        base_entries = generate_base_schedule(schedule, datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc))
        
        overrides = [
            Override(
                user="bob",
                start_at=datetime(2025, 11, 8, 9, 0, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 11, 8, 17, 0, 0, tzinfo=timezone.utc)
            ),
            Override(
                user="charlie",
                start_at=datetime(2025, 11, 8, 17, 0, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 11, 9, 9, 0, 0, tzinfo=timezone.utc)
            )
        ]
        
        entries = apply_overrides(base_entries, overrides)
        
        # Find the consecutive overrides
        bob_entry = [e for e in entries if e['user'] == 'bob'][0]
        charlie_entry = [e for e in entries if e['user'] == 'charlie'][0]
        
        assert bob_entry['end_at'] == charlie_entry['start_at']
    
    def test_multiple_overrides_in_same_shift(self):
        """Test multiple overrides within the same shift."""
        schedule = Schedule(
            users=["alice"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        base_entries = generate_base_schedule(schedule, datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc))
        
        overrides = [
            Override(
                user="bob",
                start_at=datetime(2025, 11, 8, 9, 0, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 11, 8, 12, 0, 0, tzinfo=timezone.utc)
            ),
            Override(
                user="charlie",
                start_at=datetime(2025, 11, 9, 9, 0, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 11, 9, 12, 0, 0, tzinfo=timezone.utc)
            )
        ]
        
        entries = apply_overrides(base_entries, overrides)
        
        # Alice's shift should be split into 5 parts: before bob, bob, between, charlie, after charlie
        assert len(entries) == 5
        assert entries[0]['user'] == 'alice'
        assert entries[1]['user'] == 'bob'
        assert entries[2]['user'] == 'alice'
        assert entries[3]['user'] == 'charlie'
        assert entries[4]['user'] == 'alice'


class TestTruncation:
    """Test time window truncation."""
    
    def test_truncate_start(self):
        """Test truncation at the start of a shift."""
        entries = [
            {
                'user': 'alice',
                'start_at': datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
            }
        ]
        
        from_time = datetime(2025, 11, 10, 0, 0, 0, tzinfo=timezone.utc)
        until_time = datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
        
        truncated = truncate_to_window(entries, from_time, until_time)
        
        assert len(truncated) == 1
        assert truncated[0]['start_at'] == from_time
        assert truncated[0]['end_at'] == datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
    
    def test_truncate_end(self):
        """Test truncation at the end of a shift."""
        entries = [
            {
                'user': 'alice',
                'start_at': datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
            }
        ]
        
        from_time = datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)
        until_time = datetime(2025, 11, 10, 0, 0, 0, tzinfo=timezone.utc)
        
        truncated = truncate_to_window(entries, from_time, until_time)
        
        assert len(truncated) == 1
        assert truncated[0]['start_at'] == datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)
        assert truncated[0]['end_at'] == until_time
    
    def test_truncate_both_ends(self):
        """Test truncation at both start and end."""
        entries = [
            {
                'user': 'alice',
                'start_at': datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
            }
        ]
        
        from_time = datetime(2025, 11, 8, 0, 0, 0, tzinfo=timezone.utc)
        until_time = datetime(2025, 11, 13, 0, 0, 0, tzinfo=timezone.utc)
        
        truncated = truncate_to_window(entries, from_time, until_time)
        
        assert len(truncated) == 1
        assert truncated[0]['start_at'] == from_time
        assert truncated[0]['end_at'] == until_time
    
    def test_filter_entries_outside_window(self):
        """Test that entries completely outside the window are filtered out."""
        entries = [
            {
                'user': 'alice',
                'start_at': datetime(2025, 11, 1, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)
            },
            {
                'user': 'bob',
                'start_at': datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
            },
            {
                'user': 'charlie',
                'start_at': datetime(2025, 11, 21, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 28, 17, 0, 0, tzinfo=timezone.utc)
            }
        ]
        
        from_time = datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)
        until_time = datetime(2025, 11, 21, 17, 0, 0, tzinfo=timezone.utc)
        
        truncated = truncate_to_window(entries, from_time, until_time)
        
        assert len(truncated) == 1
        assert truncated[0]['user'] == 'bob'


class TestMerging:
    """Test consecutive entry merging."""
    
    def test_merge_consecutive_same_user(self):
        """Test merging consecutive entries for the same user."""
        entries = [
            {
                'user': 'alice',
                'start_at': datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc)
            },
            {
                'user': 'alice',
                'start_at': datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
            }
        ]
        
        merged = merge_consecutive_entries(entries)
        
        assert len(merged) == 1
        assert merged[0]['user'] == 'alice'
        assert merged[0]['start_at'] == datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)
        assert merged[0]['end_at'] == datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
    
    def test_dont_merge_different_users(self):
        """Test that entries with different users are not merged."""
        entries = [
            {
                'user': 'alice',
                'start_at': datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc)
            },
            {
                'user': 'bob',
                'start_at': datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
            }
        ]
        
        merged = merge_consecutive_entries(entries)
        
        assert len(merged) == 2
    
    def test_dont_merge_non_consecutive(self):
        """Test that non-consecutive entries for the same user are not merged."""
        entries = [
            {
                'user': 'alice',
                'start_at': datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc)
            },
            {
                'user': 'bob',
                'start_at': datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 12, 17, 0, 0, tzinfo=timezone.utc)
            },
            {
                'user': 'alice',
                'start_at': datetime(2025, 11, 12, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
            }
        ]
        
        merged = merge_consecutive_entries(entries)
        
        assert len(merged) == 3
    
    def test_merge_empty_list(self):
        """Test merging empty list."""
        merged = merge_consecutive_entries([])
        assert len(merged) == 0
    
    def test_merge_multiple_consecutive(self):
        """Test merging multiple consecutive entries for the same user."""
        entries = [
            {
                'user': 'alice',
                'start_at': datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 8, 17, 0, 0, tzinfo=timezone.utc)
            },
            {
                'user': 'alice',
                'start_at': datetime(2025, 11, 8, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 9, 17, 0, 0, tzinfo=timezone.utc)
            },
            {
                'user': 'alice',
                'start_at': datetime(2025, 11, 9, 17, 0, 0, tzinfo=timezone.utc),
                'end_at': datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc)
            }
        ]
        
        merged = merge_consecutive_entries(entries)
        
        assert len(merged) == 1
        assert merged[0]['start_at'] == datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)
        assert merged[0]['end_at'] == datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc)


class TestIntegration:
    """Integration tests for the full render_schedule function."""
    
    def test_example_from_readme(self):
        """Test the exact example from the README."""
        schedule = Schedule(
            users=["alice", "bob", "charlie"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        overrides = [
            Override(
                user="charlie",
                start_at=datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 11, 10, 22, 0, 0, tzinfo=timezone.utc)
            )
        ]
        
        from_time = datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)
        until_time = datetime(2025, 11, 21, 17, 0, 0, tzinfo=timezone.utc)
        
        result = render_schedule(schedule, overrides, from_time, until_time)
        
        assert len(result) == 4
        
        # Check first entry
        assert result[0]['user'] == 'alice'
        assert result[0]['start_at'] == datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)
        assert result[0]['end_at'] == datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc)
        
        # Check override
        assert result[1]['user'] == 'charlie'
        assert result[1]['start_at'] == datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc)
        assert result[1]['end_at'] == datetime(2025, 11, 10, 22, 0, 0, tzinfo=timezone.utc)
        
        # Check alice resumes
        assert result[2]['user'] == 'alice'
        assert result[2]['start_at'] == datetime(2025, 11, 10, 22, 0, 0, tzinfo=timezone.utc)
        assert result[2]['end_at'] == datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
        
        # Check bob's turn
        assert result[3]['user'] == 'bob'
        assert result[3]['start_at'] == datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
        assert result[3]['end_at'] == datetime(2025, 11, 21, 17, 0, 0, tzinfo=timezone.utc)
    
    def test_no_overrides(self):
        """Test schedule with no overrides."""
        schedule = Schedule(
            users=["alice", "bob"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        from_time = datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)
        until_time = datetime(2025, 11, 21, 17, 0, 0, tzinfo=timezone.utc)
        
        result = render_schedule(schedule, [], from_time, until_time)
        
        assert len(result) == 2
        assert result[0]['user'] == 'alice'
        assert result[1]['user'] == 'bob'


class TestInvalidInputs:
    """Test handling of invalid inputs."""
    
    def test_empty_users_list(self):
        """Test that empty users list raises validation error."""
        with pytest.raises(ValueError, match="users list cannot be empty"):
            Schedule(
                users=[],
                handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
                handover_interval_days=7
            )
    
    def test_zero_handover_interval(self):
        """Test that zero handover interval raises validation error."""
        with pytest.raises(ValueError, match="handover_interval_days must be greater than 0"):
            Schedule(
                users=["alice"],
                handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
                handover_interval_days=0
            )
    
    def test_negative_handover_interval(self):
        """Test that negative handover interval raises validation error."""
        with pytest.raises(ValueError, match="handover_interval_days must be greater than 0"):
            Schedule(
                users=["alice"],
                handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
                handover_interval_days=-1
            )
    
    def test_override_end_before_start(self):
        """Test override where end time is before start time raises validation error."""
        with pytest.raises(ValueError, match="end_at must be after start_at"):
            Override(
                user="alice",
                start_at=datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 11, 10, 10, 0, 0, tzinfo=timezone.utc)
            )
    
    def test_override_end_equals_start(self):
        """Test override where end time equals start time raises validation error."""
        with pytest.raises(ValueError, match="end_at must be after start_at"):
            Override(
                user="alice",
                start_at=datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 11, 10, 17, 0, 0, tzinfo=timezone.utc)
            )
    
    def test_until_before_from(self):
        """Test render_schedule where until is before from."""
        schedule = Schedule(
            users=["alice"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        from_time = datetime(2025, 11, 21, 17, 0, 0, tzinfo=timezone.utc)
        until_time = datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)
        
        result = render_schedule(schedule, [], from_time, until_time)
        
        # Should return empty result
        assert len(result) == 0
    
    def test_window_before_schedule_start(self):
        """Test time window that's entirely before schedule starts."""
        schedule = Schedule(
            users=["alice"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        from_time = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
        until_time = datetime(2025, 11, 7, 0, 0, 0, tzinfo=timezone.utc)
        
        result = render_schedule(schedule, [], from_time, until_time)
        
        # Should return empty result as window is before schedule
        assert len(result) == 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_exact_time_window_match(self):
        """Test when time window exactly matches shift boundaries."""
        schedule = Schedule(
            users=["alice"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        from_time = datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)
        until_time = datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
        
        result = render_schedule(schedule, [], from_time, until_time)
        
        assert len(result) == 1
        assert result[0]['start_at'] == from_time
        assert result[0]['end_at'] == until_time
    
    def test_very_short_override(self):
        """Test a very short override (1 minute)."""
        schedule = Schedule(
            users=["alice"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        overrides = [
            Override(
                user="bob",
                start_at=datetime(2025, 11, 10, 12, 0, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 11, 10, 12, 1, 0, tzinfo=timezone.utc)
            )
        ]
        
        from_time = datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)
        until_time = datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
        
        result = render_schedule(schedule, overrides, from_time, until_time)
        
        # Should split into 3 entries: before, override, after
        assert len(result) == 3
        assert result[1]['user'] == 'bob'
        assert (result[1]['end_at'] - result[1]['start_at']).total_seconds() == 60
    
    def test_override_at_window_boundary(self):
        """Test override that starts/ends at window boundaries."""
        schedule = Schedule(
            users=["alice"],
            handover_start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=7
        )
        
        overrides = [
            Override(
                user="bob",
                start_at=datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 11, 8, 0, 0, 0, tzinfo=timezone.utc)
            )
        ]
        
        from_time = datetime(2025, 11, 7, 17, 0, 0, tzinfo=timezone.utc)
        until_time = datetime(2025, 11, 14, 17, 0, 0, tzinfo=timezone.utc)
        
        result = render_schedule(schedule, overrides, from_time, until_time)
        
        assert result[0]['user'] == 'bob'
        assert result[0]['start_at'] == from_time
    
    def test_large_number_of_users(self):
        """Test schedule with many users."""
        users = [f"user{i}" for i in range(100)]
        
        schedule = Schedule(
            users=users,
            handover_start_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            handover_interval_days=1
        )
        
        from_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        until_time = datetime(2025, 1, 11, 0, 0, 0, tzinfo=timezone.utc)
        
        result = render_schedule(schedule, [], from_time, until_time)
        
        # Should have 10 entries (10 days)
        assert len(result) == 10
        # Should cycle through first 10 users
        assert result[0]['user'] == 'user0'
        assert result[9]['user'] == 'user9'

