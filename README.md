# timesheet

Records start / stop working times

Python typing magic is used, specifically for `pyright`/`pylance` in [VS Code](https://github.com/VSCodium/vscodium). Not completely compatible with `mypy` because why would Microsoft do a silly thing like use an existing project that already has a high user base. Or let their Intellisense correctly use `mypy` options. That would just be silly.

## Current features

- Can "guess" start / stop times by parsing `/var/log/auth.log*`
- Guess can work on in or out of a single day, or backfill all missing days
- Basic overwrite / interactive validation when modifying a day with existing logs
- Can print out easy to read logs for individual or a range of days
- `print --export` gives times rounded to the nearest 15min for easy pasting into actual timesheet
- Allows using a "standard" day on backfill for days without log entries
- Tracks flex time
  - set an initial balance
    - _e.g.,_ `timesheet flex set-balance 2021-01-01 20`
    - balance is hours available at the beginning of the day
  - mark full days flexed
    - `timesheet flex day`, `timesheet flex day 2021-01-16`
  - flex hours are extracted automatically from timesheet logs
  - warns if empty work days are found when calculating the balance
- Holiday awareness by importing a calendar `.ics` file

## Installation

Because of the fancy python typing used, a minimum python version of 3.9 is required. Using
[pipx](https://pipxproject.github.io/pipx/) to install is recommended unless (or even if) you're
using python3.9 as system python. Python3.9 can be installed via conda
(`conda create -n py3.9 python==3.9`) or pyenv (`pyenv install 3.9`) or maybe even your package
manager.

```bash
# from the repo root
PIPX_DEFAULT_PYTHON=/path/to/python3.9 pipx install .
```

### Updating

```bash
# from the repo root
git pull && PIPX_DEFAULT_PYTHON=/path/to/python3.9 pipx install . --force
```

## Usage

Two executables are created on installation:

- `timesheet`: full functionality. see: `timesheet --help`
- `clock`: shortcut to `timesheet clock` for easier `clock in`, `clock out`. see: `clock --help`

## TODO:

- Mark days as PTO, sick
- Flex improvements
  - awareness of short days
  - load holidays from non-`ics` sources
- Tests
- Access excel timesheet directly
  - `--export` writes to file
  - `update-holidays` reads values for full/partial holidays
- actual nice documentation?
