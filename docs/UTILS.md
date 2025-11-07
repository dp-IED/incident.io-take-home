# Utilities Documentation

The `utils/schedule_utils.py` module contains the core scheduling logic.

## Data Models

### Schedule

Represents a rotation schedule configuration.

```python
class Schedule(pydantic.BaseModel):
    users: list[str]                # List of usernames in rotation order
    handover_start_at: datetime     # When the first shift begins
    handover_interval_days: int     # Days each person is on-call
```

**Validation:**

- `users` cannot be empty
- `handover_interval_days` must be greater than 0

### Override

Represents a temporary shift change.

```python
class Override(pydantic.BaseModel):
    user: str           # Who's taking the override shift
    start_at: datetime  # Override start time
    end_at: datetime    # Override end time
```

**Validation:**

- `end_at` must be after `start_at`

## Core Functions

### render_schedule()

Main entry point that orchestrates the scheduling algorithm.

```python
def render_schedule(
    schedule: Schedule,
    overrides: list[Override],
    from_time: datetime,
    until_time: datetime
) -> list[dict]
```

**Returns:** List of schedule entries, each with `user`, `start_at`, and `end_at`.

**Algorithm:**

1. Generate base schedule shifts
2. Apply overrides (splits shifts as needed)
3. Truncate to requested time window
4. Merge consecutive entries by the same user

### generate_base_schedule()

Creates the basic rotation pattern without overrides.

```python
def generate_base_schedule(
    schedule: Schedule,
    until_time: datetime
) -> list[dict]
```

Loops through users in order, assigning each person a shift of `handover_interval_days` duration. Continues generating shifts until reaching `until_time`.

### apply_overrides()

Applies override modifications to base schedule entries.

```python
def apply_overrides(
    base_entries: list[dict],
    overrides: list[Override]
) -> list[dict]
```

For each override that overlaps with a scheduled shift:

1. Keeps the part before the override (if any)
2. Inserts the override period
3. Keeps the part after the override (if any)

This can split one shift into multiple entries.

### truncate_to_window()

Clips schedule entries to fit within the requested time range.

```python
def truncate_to_window(
    entries: list[dict],
    from_time: datetime,
    until_time: datetime
) -> list[dict]
```

- Removes entries completely outside the window
- Adjusts start/end times of partially overlapping entries

### merge_consecutive_entries()

Combines adjacent shifts by the same person.

```python
def merge_consecutive_entries(entries: list[dict]) -> list[dict]
```

If Alice has shifts from 9am-12pm and 12pm-5pm (maybe due to an override that fell through), this merges them into one 9am-5pm shift.

## Usage Example

```python
from datetime import datetime, timezone
from utils import Schedule, Override, render_schedule

# Define schedule
schedule = Schedule(
    users=["alice", "bob"],
    handover_start_at=datetime(2025, 11, 7, 17, 0, tzinfo=timezone.utc),
    handover_interval_days=7
)

# Define overrides
overrides = [
    Override(
        user="bob",
        start_at=datetime(2025, 11, 10, 17, 0, tzinfo=timezone.utc),
        end_at=datetime(2025, 11, 10, 22, 0, tzinfo=timezone.utc)
    )
]

# Generate schedule
entries = render_schedule(
    schedule=schedule,
    overrides=overrides,
    from_time=datetime(2025, 11, 7, 17, 0, tzinfo=timezone.utc),
    until_time=datetime(2025, 11, 21, 17, 0, tzinfo=timezone.utc)
)

# entries is now a list of dicts with user, start_at, end_at
```

## Design Decisions

**Why split overrides into a separate step?**

Separating base schedule generation from override application makes the code easier to test and understand. You can verify the rotation works correctly before adding override complexity.

**Why merge consecutive entries?**

When an override splits a shift, sometimes the result leaves the original person with multiple consecutive segments. Merging these back together produces cleaner output and matches the expected behavior.

**Why use Pydantic models?**

Pydantic provides automatic validation and parsing of JSON input, reducing boilerplate code and catching configuration errors early.

## Testing

The test suite in `tests/test_schedule.py` covers:

- Basic rotations (daily, weekly, multi-week)
- Single and multiple overrides
- Edge cases (overrides at shift boundaries, outside time window)
- Window truncation
- Entry merging
- Input validation

Run tests with: `pytest tests/`
