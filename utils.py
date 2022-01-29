import logging
import requests
from icalendar import Calendar
import recurring_ical_events
import arrow
import datetime


def fetch_events(calendar, start_time, end_time):
    logging.debug(f"==> checking calendar {calendar}")

    raw_cal = requests.get(calendar).text
    ical = Calendar.from_ical(raw_cal)
    events = recurring_ical_events.of(ical).between(start_time.date(), end_time.date())

    logging.debug(f" - adding {len(events)} events")
    return events


def make_printable_events(events):
    printable_events = []
    for event in events:
        summary = event.decoded("summary").decode("utf-8")

        start = event["DTSTART"].dt
        duration = event["DTEND"].dt - event["DTSTART"].dt
        print(summary, event["DTSTART"], event["DTEND"])
        starttime = ""
        # this is a clunky way of differentiating all-day events from ones with hours
        if duration.total_seconds() < 86400:
            starthour = (
                arrow.get(start).to("US/Central").format("h")
                if isinstance(start, datetime.datetime)
                else arrow.get(start).format("h")
            )
            sm = arrow.get(start).to("US/Central").format("mm")
            startminute = "" if sm == "00" else sm

            suffix = "p"
            if arrow.get(start).to("US/Central").format("a") == "am":
                suffix = "a"
            starttime += starthour + startminute + suffix + " "
        printable_line = f"{starttime}{summary}"
        logging.debug(f" - Adding event {printable_line}")
        printable_events.append(printable_line)
    return printable_events
