# timesheet

Records start / stop working times

-   Can "guess" start / stop times by parsing `/var/log/auth.log*`
-   Guess can work on in or out of a single day, or backfill all missing days
-   Basic overwrite / interactive validation when modifying a day with existing logs
-   Can print out easy to red logs for individual or a range of days
-   `--export` prints a month out for easy pasting into my timesheet

TODO:

-   Allow using a "standard" day for regular working hours
-   Show current flex time balance
-   Log in flex time used, so balance reflects reality
-   Mark days for PTO, sick, public holidays
