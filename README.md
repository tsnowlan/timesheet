# timesheet

Records start / stop working times

## Current features

- Can "guess" start / stop times by parsing `/var/log/auth.log*`
- Guess can work on in or out of a single day, or backfill all missing days
- Basic overwrite / interactive validation when modifying a day with existing logs
- Can print out easy to read logs for individual or a range of days
- `print --export` gives times rounded to the nearest 15min for easy pasting into actual timesheet
- Allows using a "standard" day on backfill for days without log entries

## Installation

Recommend using [pipx](https://pipxproject.github.io/pipx/) unless (or even if) using python3.9 in your base environment

```bash
# from the repo root
PIPX_DEFAULT_PYTHON=/path/to/python3.9 pipx install .
```

### Updating

```bash
# from the repo root
git pull && PIPX_DEFAULT_PYTHON=/path/to/python3.9 pipx install . --force
```

## TODO:

- Show current flex time balance
- Log flex time used, so balance reflects reality
- Mark days as PTO, sick, public holidays
- Tests
- Write logs directly to excel timesheet?
- switch to logging instead of plain prints
