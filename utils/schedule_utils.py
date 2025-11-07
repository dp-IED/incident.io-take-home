"""Utility functions for processing schedule entries."""

from datetime import datetime, timedelta
import pydantic


class Schedule(pydantic.BaseModel):
    users: list[str]
    handover_start_at: datetime
    handover_interval_days: int
    
    @pydantic.field_validator('handover_interval_days')
    @classmethod
    def validate_handover_interval(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('handover_interval_days must be greater than 0')
        return v
    
    @pydantic.field_validator('users')
    @classmethod
    def validate_users(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError('users list cannot be empty')
        return v


class Override(pydantic.BaseModel):
    user: str
    start_at: datetime
    end_at: datetime
    
    @pydantic.model_validator(mode='after')
    def validate_time_order(self) -> 'Override':
        if self.end_at <= self.start_at:
            raise ValueError('end_at must be after start_at')
        return self


def generate_base_schedule(schedule: Schedule, until_time: datetime) -> list[dict]:
    """
    Generate base schedule entries based on the rotation configuration.
    
    This creates shifts for each user in rotation, starting from handover_start_at
    and continuing until we reach or exceed until_time.
    
    Args:
        schedule: The schedule configuration with users and handover details
        until_time: Generate shifts up to this time
        
    Returns:
        List of schedule entries with user, start_at, and end_at
    """
    base_entries = []
    current_time = schedule.handover_start_at
    user_index = 0
    
    # Generate shifts up to the until_time
    while current_time < until_time:
        shift_end = current_time + timedelta(days=schedule.handover_interval_days)
        base_entries.append({
            'user': schedule.users[user_index % len(schedule.users)],
            'start_at': current_time,
            'end_at': shift_end
        })
        current_time = shift_end
        user_index += 1
    
    return base_entries


def apply_overrides(base_entries: list[dict], overrides: list[Override]) -> list[dict]:
    """
    Apply overrides to base schedule entries by splitting shifts.
    
    When an override overlaps with a scheduled shift, we:
    1. Keep the part of the shift before the override
    2. Insert the override
    3. Keep the part of the shift after the override
    
    Time complexity: O(n × k + m log m)
    n = number of shifts in base schedule, 
    m = number of overrides, 
    k = average number of overrides per shift
    
    Args:
        base_entries: Base schedule entries to modify
        overrides: List of override periods
        
    Returns:
        Modified schedule entries with overrides applied
    """
    if not overrides:
        return base_entries
    
    # Sort all overrides once by start time (O(m log m))
    sorted_overrides = sorted(overrides, key=lambda o: o.start_at)
    
    final_entries = []
    
    for entry in base_entries:
        # Find overrides for this shift using the sorted list
        overlapping_overrides = [
            o for o in sorted_overrides
            if o.start_at < entry['end_at'] and o.end_at > entry['start_at']
        ]
        
        if not overlapping_overrides:
            final_entries.append(entry) # do nothing
        else:
            # Split the entry to insert override
            current_start = entry['start_at']
            
            for override in overlapping_overrides:
                if current_start < override.start_at:
                    final_entries.append({
                        'user': entry['user'],
                        'start_at': current_start,
                        'end_at': override.start_at
                    })
                
                final_entries.append({
                    'user': override.user,
                    'start_at': override.start_at,
                    'end_at': override.end_at
                })
                
                current_start = override.end_at
            
            if current_start < entry['end_at']:
                final_entries.append({
                    'user': entry['user'],
                    'start_at': current_start,
                    'end_at': entry['end_at']
                })
    
    return final_entries


def render_schedule(schedule: Schedule, overrides: list[Override], from_time: datetime, until_time: datetime) -> list[dict]:
    """
    Generate schedule entries with overrides applied.
    
    Algorithm:
    1. Generate base schedule shifts for all users in the rotation
    2. Check for overrides and apply modifications if any exist
    3. Truncate to the requested time window
    4. Merge consecutive entries with the same user
    
    Args:
        schedule: Schedule configuration
        overrides: List of override periods
        from_time: Start of requested time window
        until_time: End of requested time window
        
    Returns:
        Final schedule entries as a list of dicts
    """
    # Step 1: Generate base schedule
    base_entries = generate_base_schedule(schedule, until_time)
    
    # Step 2: Check for overrides and apply them
    if overrides:
        entries_with_overrides = apply_overrides(base_entries, overrides)
    else:
        entries_with_overrides = base_entries
    
    # Step 3: Truncate to the requested time window
    truncated_entries = truncate_to_window(entries_with_overrides, from_time, until_time)
    
    # Step 4: Merge consecutive entries with the same user
    merged_entries = merge_consecutive_entries(truncated_entries)
    
    return merged_entries


def truncate_to_window(entries: list[dict], from_time: datetime, until_time: datetime) -> list[dict]:
    """
    Truncate schedule entries to fit within the requested time window.
    
    Args:
        entries: Schedule entries to truncate
        from_time: Start of the time window
        until_time: End of the time window
        
    Returns:
        Entries truncated to the time window
    """
    truncated_entries = []
    for entry in entries:
        if entry['end_at'] <= from_time or entry['start_at'] >= until_time:
            continue
        
        # fit within the window
        truncated_entry = {
            'user': entry['user'],
            'start_at': max(entry['start_at'], from_time),
            'end_at': min(entry['end_at'], until_time)
        }
        truncated_entries.append(truncated_entry)
    
    return truncated_entries


def merge_consecutive_entries(entries: list[dict]) -> list[dict]:
    """
    Merge consecutive entries with the same user.
    
    If a user has multiple consecutive shifts (e.g., due to override splits),
    combine them into a single entry.
    
    Args:
        entries: Schedule entries to merge
        
    Returns:
        Merged schedule entries
    """
    if not entries:
        return []
    
    merged_entries = []
    current_merged = entries[0].copy()
    
    for entry in entries[1:]:
        if entry['user'] == current_merged['user'] and entry['start_at'] == current_merged['end_at']:
            # Merge
            current_merged['end_at'] = entry['end_at']
        else:
            merged_entries.append(current_merged)
            current_merged = entry.copy()
    
    merged_entries.append(current_merged)
    
    return merged_entries

