import click
import datetime

# clock in [ TIMESTAMP ] [ --guess ]]
@click.group(help="clocking in or out")
def clock():
    pass

@clock.command()
@click.argument(
    "date_time",
    default=datetime.datetime.now()
)
@click.option(
    "-g", "--guess", is_flag=True, help="Guess login time from auth logs"
)
def in(date_time, guess):
    pass

@clock.command()
@click.argument(
    "date_time",
    default=datetime.datetime.now()
)
def out(date_time):
    pass

@click.group(help="print out timesheet entries")
def show_log():
    pass
