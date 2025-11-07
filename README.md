# On-Call Schedule Renderer

## [Video Walkthrough](https://www.loom.com/share/ba6c9051ee71423b99804237379e3d2d)

A Python tool that generates on-call schedules with support for shift rotations and overrides.

## What it does

Given a schedule configuration (users, start time, rotation interval) and optional overrides (temporary shift changes), this tool outputs who's on-call during any time period you specify.

## Quick Start

The zip file includes a virtual environment, so you can directly run the following command:

```bash
source .venv/bin/activate
```

Then, run the scheduler with the following command:

```bash
./render_schedule \
    --schedule=your_schedule.json \
    --overrides=your_overrides.json \
    --from='2025-11-07T17:00:00Z' \
    --until='2025-11-21T17:00:00Z'
```

You can also use the example files in the `example` directory to generate the schedule for the given time period, this will reproduce the example from the README.

```bash
./render_schedule \
    --schedule=example/schedule.json \
    --overrides=example/overrides.json \
    --from='2025-11-07T17:00:00Z' \
    --until='2025-11-21T17:00:00Z'
```

## Installation

I recommend using a virtual environment to install the dependencies:

```bash
python -m venv venv
source venv/bin/activate
```

Then, install dependencies:

```bash
pip install -r requirements.txt
```

Run the scheduler with the following command:

```bash
./render_schedule \
    --schedule=example/schedule.json \
    --overrides=example/overrides.json \
    --from='2025-11-07T17:00:00Z' \
    --until='2025-11-21T17:00:00Z'
```

This outputs a JSON array showing who's on-call for each time period.

## How it works

The scheduler follows a simple 4-step process:

1. **Generate base shifts** - Creates rotating shifts for all users based on the handover interval
2. **Apply overrides** - Splits shifts when someone else takes over temporarily
3. **Truncate to window** - Clips entries to match your requested time range
4. **Merge consecutive** - Combines adjacent shifts by the same person

## Schedule Format

A schedule defines the rotation pattern:

```json
{
  "users": ["alice", "bob", "charlie"],
  "handover_start_at": "2025-11-07T17:00:00Z",
  "handover_interval_days": 7
}
```

Users rotate through shifts in order. Each person gets one shift of the specified duration, then it moves to the next person.

## Override Format

Overrides let someone cover part of another person's shift:

```json
[
  {
    "user": "charlie",
    "start_at": "2025-11-10T17:00:00Z",
    "end_at": "2025-11-10T22:00:00Z"
  }
]
```

## Installation

The tool requires Python 3.10+. Install dependencies:

```bash
pip install -r requirements.txt
```

Make the script executable:

```bash
chmod +x render_schedule
```

## Testing

Run the test suite:

```bash
pytest tests/
```
