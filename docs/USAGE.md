# Usage Guide

The `render_schedule` script takes four required arguments:

```bash
./render_schedule \
    --schedule <path-to-schedule.json> \
    --overrides <path-to-overrides.json> \
    --from <start-time> \
    --until <end-time>
```

- `--schedule` - Path to JSON file defining the rotation schedule
- `--overrides` - Path to JSON file with override shifts (can be an empty array `[]`)
- `--from` - Start time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SSZ`)
- `--until` - End time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SSZ`)

All arguments are required.

The script will output a JSON array of schedule entries, applying the overrides to the base schedule, truncating to the requested time window, and merging consecutive entries with the same user. Implementation details are in the [Utils Documentation](UTILS.md).

## Examples

### Basic weekly rotation

Schedule file (`schedule.json`):

```json
{
  "users": ["alice", "bob"],
  "handover_start_at": "2025-11-07T17:00:00Z",
  "handover_interval_days": 7
}
```

No overrides (`overrides.json`):

```json
[]
```

Command:

```bash
./render_schedule \
    --schedule schedule.json \
    --overrides overrides.json \
    --from '2025-11-07T17:00:00Z' \
    --until '2025-11-21T17:00:00Z'
```

Output:

```json
[
  {
    "user": "alice",
    "start_at": "2025-11-07T17:00:00Z",
    "end_at": "2025-11-14T17:00:00Z"
  },
  {
    "user": "bob",
    "start_at": "2025-11-14T17:00:00Z",
    "end_at": "2025-11-21T17:00:00Z"
  }
]
```

### With an override

Add an override (`overrides.json`):

```json
[
  {
    "user": "bob",
    "start_at": "2025-11-10T17:00:00Z",
    "end_at": "2025-11-10T22:00:00Z"
  }
]
```

Output:

```json
[
  {
    "user": "alice",
    "start_at": "2025-11-07T17:00:00Z",
    "end_at": "2025-11-10T17:00:00Z"
  },
  {
    "user": "bob",
    "start_at": "2025-11-10T17:00:00Z",
    "end_at": "2025-11-10T22:00:00Z"
  },
  {
    "user": "alice",
    "start_at": "2025-11-10T22:00:00Z",
    "end_at": "2025-11-14T17:00:00Z"
  },
  {
    "user": "bob",
    "start_at": "2025-11-14T17:00:00Z",
    "end_at": "2025-11-21T17:00:00Z"
  }
]
```

Notice how Bob's override splits Alice's shift into two parts.

### Different rotation intervals

Daily rotation (24 hours):

```json
{
  "users": ["alice", "bob", "charlie"],
  "handover_start_at": "2025-11-07T09:00:00Z",
  "handover_interval_days": 1
}
```

Two-week rotation:

```json
{
  "users": ["alice", "bob"],
  "handover_start_at": "2025-11-07T17:00:00Z",
  "handover_interval_days": 14
}
```

## Common Patterns

### Viewing current on-call

To see who's on-call right now:

```bash
./render_schedule \
    --schedule schedule.json \
    --overrides overrides.json \
    --from '2025-11-07T12:00:00Z' \
    --until '2025-11-07T13:00:00Z'
```

### Planning ahead

Get the next month's schedule:

```bash
./render_schedule \
    --schedule schedule.json \
    --overrides overrides.json \
    --from '2025-11-01T00:00:00Z' \
    --until '2025-12-01T00:00:00Z'
```

## Error Handling

The script validates input and provides helpful error messages:

- **Missing files** - Shows usage instructions
- **Invalid JSON** - Reports parsing errors
- **Invalid dates** - Must be in `YYYY-MM-DDTHH:MM:SSZ` format
- **Empty user list** - Schedule must have at least one user
- **Invalid interval** - Handover interval must be greater than 0
- **Invalid override times** - Override end time must be after start time

## Output Format

The script always outputs valid JSON. Each entry contains:

- `user` - Username as a string
- `start_at` - ISO 8601 timestamp
- `end_at` - ISO 8601 timestamp

Entries are returned in chronological order with no gaps or overlaps.
