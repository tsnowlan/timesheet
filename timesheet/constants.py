import datetime

# dates
ONE_DAY = datetime.timedelta(days=1)
TODAY = datetime.date.today()
TOMORROW = TODAY + ONE_DAY
YESTERDAY = TODAY - ONE_DAY

# formatting
TIME_FORMATS = ["%H:%M"]
for suffix in [":%S", ".%f"]:
    TIME_FORMATS.append(f"{TIME_FORMATS[-1]}{suffix}")
DATE_FORMATS = ["%Y-%m-%d"]
for tf in TIME_FORMATS:
    DATE_FORMATS.append(f"{DATE_FORMATS[0]} {tf}")
DATETIME_FORMATS = TIME_FORMATS + DATE_FORMATS
ROW_HEADER = f"{'Date': <8}\t{'Clock In': <8}\t{'Clock Out': <8}"
