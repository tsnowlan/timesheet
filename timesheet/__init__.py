import datetime
from pathlib import Path

from .models import Timesheet

TODAY = datetime.date.today()
DEF_DBFILE = Path().home() / "timesheet.db"
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
UNLOCK_STR = "unlocked login keyring"
LOGIN_STR = "gnome-keyring-daemon started properly and unlocked keyring"
LIDCLOSE_STR = "Lid closed"
SHUTDOWN_STR = "System is powering down"