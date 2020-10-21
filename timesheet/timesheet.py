#!/usr/bin/env python3

import argparse
import datetime
from datetime import timedelta
from operator import and_
from pathlib import Path
import re
from sqlite3.dbapi2 import Time
from sqlalchemy import create_engine, Column, Date, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
import sqlite3

# sqlalchemy shit
Base = declarative_base()
Session = sessionmaker()

# globals
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


def main():
    parser = argparse.ArgumentParser()
    in_out = parser.add_mutually_exclusive_group(required=True)
    in_out.add_argument(
        "-i", "--clock-in", dest="clock_in", action="store_true", help="clock in"
    )
    in_out.add_argument(
        "-o", "--clock-out", dest="clock_out", action="store_true", help="clock out"
    )
    in_out.add_argument(
        "-e",
        "--edit",
        action="store_true",
        help="edit the time of the specified or more recent date",
    )
    in_out.add_argument(
        "--show",
        metavar="today | month | all",
        nargs="?",
        const="today",
        help="Show clock in/out for the given date",
    )
    in_out.add_argument("-b", "--balance", action="store_true", help="flextime balance")
    in_out.add_argument(
        "-p",
        "--print",
        metavar="month | MONTH_NAME",
        nargs="?",
        const="month",
        help="Print out times to paste into fleksitid sheet",
    )
    parser.add_argument(
        "-l",
        "--from-log",
        dest="from_log",
        action="store_true",
        help="Set clock in from auth.log",
    )
    parser.add_argument(
        "-s",
        "--from-string",
        dest="from_string",
        type=date_string,
        help="Set clock in/out from datestring",
    )
    parser.add_argument(
        "-std",
        "--standard-day",
        dest="is_standard",
        action="store_true",
        help="Set hours to 9-16:30 of current or specified date, can use --offset to adjust",
    )
    parser.add_argument("--offset", type=time_delta, help="offset standard day by XhYm")
    parser.add_argument(
        "-d",
        "--dbfile",
        type=Path,
        default=DEF_DBFILE,
        help="Specify which db file to use. Default: {}".format(DEF_DBFILE),
    )
    parser.add_argument("--verbose", action="store_true", help="be extra chatty")
    parser.add_argument("--debug", action="store_true", help="run in debug mode")
    args = parser.parse_args()

    if args.debug:
        setattr(args, "verbose", True)

    engine = create_engine(f"sqlite:///{args.dbfile}", echo=True)
    Session.configure(bind=engine)
    session = Session()
    default_sort = (Timesheet.clock,)

    if args.show or args.print:
        target = args.show if args.show else args.print
        if target == "today":
            res = (
                session.query(Timesheet)
                .filter(Timesheet.date == TODAY)
                .order_by(*default_sort)
            )
        elif target == "month":
            res = get_month().order_by(*default_sort)
        elif target == "all":
            res = session.query(Timesheet).order_by(*default_sort)
        elif target in MONTHS:
            res = get_month(MONTHS[target.lower()]).order_by(*default_sort)
        else:
            raise ValueError(f"Unrecognized target: {target}")

        entries = res.all()
        if entries:
            output = {}
            for e in entries:
                if e[0] not in output:
                    output[e[0]] = {"IN": None, "OUT": None}
                output[e[0]][e[1]] = datetime.datetime.strptime(
                    e[2], "%Y-%m-%d %H:%M:%S"
                )
            if args.show:
                for dt in output:
                    print("{}\t{}\t{}".format(dt, output[dt]["IN"], output[dt]["OUT"]))
            else:
                out_str = ""
                for action in ("IN", "OUT"):
                    out_str += "Print {}:\n---\n".format(action)
                    for day in range(1, 32):
                        try:
                            d = min_date.replace(day=day).strftime("%Y-%m-%d")
                        except ValueError as e:
                            if "is out of range for month" in str(e):
                                break
                            else:
                                raise (e)
                        if d in output and output[d][action]:
                            rounded = round_min(output[d])
                            out_str += "{}\t{}\n".format(
                                rounded[action].hour, rounded[action].minute
                            )
                        else:
                            out_str += "\n"
                    if action == "IN":
                        out_str = out_str.strip() + "\n\n---\n"
                print(out_str.strip())

        else:
            print("No entries found for query: {}, {}".format(query, qargs))
    elif args.balance:
        conn.row_factory = dict_factory
        qry = """
            SELECT ds, type, clock
            FROM timesheet
            ORDER BY 1, 3
        """.strip()
        c = conn.cursor()
        c.execute(qry)

        entries = c.fetchall()
        dates = {}
        for e in entries:
            ds_str = str(e["ds"])
            ts = datetime.datetime.strptime(e["clock"], "%Y-%m-%d %H:%M:%S")
            if ds_str in dates:
                dates[ds_str][e["type"]] = ts
            else:
                dates[ds_str] = {e["type"]: ts}

        flex_balance = datetime.timedelta()
        flex_thresh = datetime.timedelta(hours=7.5)
        for dt in dates:
            if "IN" in dates[dt] and "OUT" in dates[dt]:
                rounded = round_min(dates[dt])
                print(
                    f'{dt} | {hm(dates[dt]["IN"])} - {hm(dates[dt]["OUT"])}  ->  {hm(rounded["IN"])} - {hm(rounded["OUT"])}'
                )
                delta = rounded["OUT"] - rounded["IN"] - flex_thresh
                if delta.seconds < 0:
                    print("Negative flex balance :( {}".format(delta))
                flex_balance += delta
        print(
            "Current flex balance: {}h{}m".format(
                flex_balance.seconds // 3600, int(flex_balance.seconds % 3600 / 60)
            )
        )
    elif args.edit:
        # TODO: specify a date/action to edit
        if args.from_string is None:
            raise ValueError(
                "You must specify -s or --from-string with the value to insert"
            )
        c = conn.cursor()
        old_entry = c.execute(
            "SELECT ds, type, clock FROM timesheet ORDER BY 3 DESC LIMIT 1"
        ).fetchone()
        qargs = (args.from_string,) + old_entry
        c.execute(
            "UPDATE timesheet SET clock = ? WHERE ds = ? AND type = ? AND clock = ?",
            qargs,
        )
        conn.commit()
        print("Updated {} to {}".format(old_entry, args.from_string))
    else:
        try:
            initdb(conn)
            ts = datetime.datetime.now().replace(second=0, microsecond=0)
            if args.from_log:
                log_ts = ts_from_log()
                if log_ts is None:
                    raise ValueError("No unlock found today: {}".format(TODAY))
                ts = log_ts
            elif args.from_string:
                ts = args.from_string

            if args.clock_in:
                action = "IN"
            else:
                action = "OUT"

            c = conn.cursor()
            c.execute(
                "INSERT INTO timesheet (ds, type, clock) VALUES (?, ?, ?)",
                [ts.date(), action, ts],
            )
            conn.commit()

            print("Clocked {} at {}".format(action, ts.strftime("%Y-%m-%d %H:%M")))
        except sqlite3.IntegrityError as e:
            old_entry = c.execute(
                "SELECT clock FROM timesheet WHERE ds = ? AND type = ?",
                [ts.date(), action],
            ).fetchone()
            print(
                "You have already clocked {} for {} at {}".format(
                    action, ts.date(), old_entry[0].split(" ")[1]
                )
            )


def get_month(
    session: scoped_session, month: int = TODAY.month, year: int = TODAY.year
):
    min_date = datetime.datetime(year=year, month=month, day=1)
    if min_date.month < 12:
        max_date = min_date.replace(month=min_date.month + 1)
    else:
        max_date = min_date.replace(year=min_date.year + 1, month=1)

    return session.query(Timesheet).filter(
        and_(Timesheet.date >= min_date, Timesheet.date < max_date)
    )


def backfill(month: int, year: int = TODAY.year):
    min_date = datetime.date(year, month, 1)
    max_date = min_date.replace(
        month=month + 1 if month < 12 else 1
    ) - datetime.timedelta(days=1)
    for curr_day in daterange(min_date, max_date):
        if curr_day.weekday() > 4:
            continue


def daterange(start_date: datetime.date, end_date: datetime.date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + datetime.timedelta(n)


def ts_from_log():
    log_files = (Path("/var/log/auth.log"), Path("/var/log/auth.log.1"))
    now = datetime.datetime.now()
    min_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    entries = []
    for logfile in log_files:
        if logfile.exists():
            with logfile.open("rt") as authlog:
                for logline in authlog:
                    if UNLOCK_STR in logline or LOGIN_STR in logline:
                        groups = re.match(r"(\w{3}) +(\d{1,2}) (\d{2}:\d{2})", logline)
                        if groups:
                            mon, dy, time = groups.groups()
                            tstr = "{} {:02d} {}".format(
                                mon.capitalize(), int(dy), time
                            )
                            ts = datetime.datetime.strptime(
                                tstr, "%b %d %H:%M"
                            ).replace(year=TODAY.year)
                            if ts > min_time:
                                entries.append(ts)
    if entries:
        return sorted(entries)[0]


def hm(dt):
    return dt.strftime("%H:%M")


def initdb(conn):
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS timesheet (
        ds DATE,
        type TEXT,
        clock DATETIME
    )
    """.strip()
    )
    c.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ds_type_idx ON timesheet (ds, type)
    """.strip()
    )
    conn.commit()


def time_delta(time_str):
    groups = re.search("^(\d+h)?(\d+m)?$")


def db_conn(dbfile):
    return sqlite3.connect(dbfile)


###


def date_string(ds):
    re_ymd = re.compile("\d{4}-\d{2}-\d{2}$")
    re_ds = re.compile("\d{4}-\d{2}-\d{2} \d{1,2}:\d{2}")
    re_ds_cap = re.compile("(\d{4}-\d{2}-\d{2} \d{1,2}:\d{2})")
    re_ts = re.compile("\d{1,2}:\d{2}$")
    parsed = None
    if re.match(re_ts, ds):
        hr, min = [int(x) for x in ds.split(":")]
        parsed = datetime.datetime.now().replace(
            hour=hr, minute=min, second=0, microsecond=0
        )
        return parsed
    elif re.match(re_ds, ds):
        ds_str = re.match(re_ds_cap, ds).groups()[0]
        parsed = datetime.datetime.strptime(ds_str, "%Y-%m-%d %H:%M")
        return parsed
    elif re.match(re_ymd, ds):
        return datetime.datetime.strptime(ds, "%Y-%m-%d")

    raise argparse.ArgumentTypeError("{0} is not a valid date string.".format(ds))


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def round_min(x, base=15):
    thresh = {"IN": 10, "OUT": 5}
    new_x = x.copy()
    for action in new_x:
        if new_x[action] is None:
            continue
        rem = new_x[action].minute % base
        if rem <= thresh[action]:
            new_x[action] -= datetime.timedelta(minutes=rem)
        else:
            new_x[action] += datetime.timedelta(minutes=base - rem)

    return new_x


class Timesheet(Base):
    __tablename__ = "timesheet"

    date = Column("ds", Date, primary_key=True, nullable=False)
    log_type = Column("type", Text, primary_key=True, nullable=False)
    clock = Column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Timesheet date={self.date} log_type={self.log_type} clock={self.clock}>"
        )

    def __str__(self) -> str:
        return f"{self.date}\t{self.log_type}\t{self.clock}"


class Timesheet2(Base):
    __tablename__ = "timesheet"

    date = Column(Date, primary_key=True)
    clock_in = Column(DateTime)
    clock_out = Column(DateTime)

    def __repr__(self) -> str:
        return f"<Timesheet date={self.date} in={self.clock_in} out={self.clock_out}"

    def __str__(self) -> str:
        return f"{self.date}\t{self.clock_in}\t{self.clock_out}"


###


if __name__ == "__main__":
    main()
