# timesheet

Records start / stop working times, with some auto detection based on log activity.

## Current features

- Can "guess" start / stop times by parsing `/var/log/auth.log*`
- Guess can work on in or out of a single day, or backfill all missing days
- Basic overwrite / interactive validation when modifying a day with existing logs
- Can print out easy to read logs for individual or a range of days
- `print --export` gives times rounded to the nearest 15min for easy pasting into actual timesheet
- Allows using a "standard" day on backfill for days without log entries
- Tracks flex time
  - set an initial balance
    - _e.g.,_ `timesheet balance set 2021-01-01 20`
    - balance is hours available at the beginning of the day
  - mark full days flexed
    - flex current day: `timesheet flex`
    - unflex a day: `timesheet flex --unflex 2021-01-05`
  - flexed hours are extracted automatically from timesheet logs
  - warns if empty work days are found when calculating the balance
- Holiday awareness by importing a calendar `.ics` file

## Installation

```bash
# from the repo root
pipx install --python "$(which python3.9)" -e .[dev]
```

### Updating

As with installing, but add `--force` to install update over previous version.

```bash
# from the repo root
git pull && pipx install --python "$(which python3.9)" -e .[dev] --force
```

## Usage

Two executables are created on installation:

- `timesheet`: full functionality. see: `timesheet --help`
- `clock`: shortcut to `timesheet clock` for easier `clock in`, `clock out`. see: `clock --help`

## TODO:

- update python/Pipfile
- integrate with Toggl
- auto holiday detection
