import logging
from time import time
from tkinter.tix import X_REGION, Y_REGION
import requests
from icalendar import Calendar
import recurring_ical_events
import arrow
import datetime
from PIL import Image, ImageDraw, ImageFont
import yaml

with open("tidbyt.yaml") as f:
    TIDBYT_CREDS = yaml.load(f, Loader=yaml.FullLoader)

# TC_FILE = open("tidybt_creds.json")
# TIDBYT_CREDS = json.load(TC_FILE)

DEVICE_ID = TIDBYT_CREDS["tidbyt_id"]
INSTALLATION_ID = TIDBYT_CREDS["tidbyt_installation"]
LOCALTZ = TIDBYT_CREDS.get("timezone", "US/Central")

BASE_URL = f"https://api.tidbyt.com/v0/devices/{DEVICE_ID}"
LIST_URL = f"{BASE_URL}/installations"
PUSH_URL = f"{BASE_URL}/push"

# Filename to write the single animated events gif
EVENTS_PIC = "todays_events.gif"

FBCAL = TIDBYT_CREDS["freeBusyCal"]

# Fonts
FONT_FILE = TIDBYT_CREDS.get("font", "fonts/tb-8.pil")
FONT = ImageFont.load(FONT_FILE)
NUMBER_OF_LINES = TIDBYT_CREDS.get("number_of_lines", 4)

IMG_WIDTH = 64
IMG_HEIGHT = 32

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TIDBYT_CREDS['tidbyt_key']}",
}

WEEKDAYS = {"1": "M", "2": "T", "3": "W", "4": "T", "5": "F", "6": "S", "7": "S"}


def always_datetime(d):
    return arrow.get(d.decoded("dtstart"))


def draw_week_ahead():
    img = Image.new("RGBA", (IMG_WIDTH, IMG_HEIGHT))
    d = ImageDraw.Draw(img)
    this_font = ImageFont.load("fonts/6x9.pil")

    for i in range(7):
        day_of_week = arrow.utcnow().shift(days=i).to("US/Central").format("d")
        day = WEEKDAYS[day_of_week]
        d.text(xy=(1 + i * 9, 0), text=day, font=this_font, fill="#333")
    return img


def draw_week_events(img, events):
    d = ImageDraw.Draw(img)

    tf = arrow.now(LOCALTZ).floor("day")

    for e in events:
        shift_start = e.decoded("dtstart") - tf
        shift_end = e.decoded("dtend") - tf

        days_forward = shift_start.days
        x_start = days_forward * 9
        x_end = x_start + 7

        hour_start = shift_start.seconds // 3600
        hour_end = shift_end.seconds // 3600
        y_start = 8 + hour_start
        y_end = 8 + hour_end

        if shift_start.days == shift_end.days:
            # this is a same-day shift; one rectangle
            d.rounded_rectangle([x_start, y_start, x_end, y_end], fill="#4640ff")
        else:
            # draw a rectangle to finish the day
            d.rounded_rectangle([x_start, y_start, x_end, 32], fill="#4640ff")
            # and another at the top of the next day, unless it's the last day
            if shift_end.days < 7:
                d.rounded_rectangle([x_start + 9, 8, x_end + 9, y_end], fill="#4640ff")

    img.save("test_week.gif")


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
