import logging
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

BASE_URL = f"https://api.tidbyt.com/v0/devices/{DEVICE_ID}"
LIST_URL = f"{BASE_URL}/installations"
PUSH_URL = f"{BASE_URL}/push"

# Filename to write the single animated events gif
EVENTS_PIC = "todays_events.gif"

# Fonts
FONT_FILE = TIDBYT_CREDS.get("font", "fonts/4x6.pil")
FONT = ImageFont.load(FONT_FILE)
NUMBER_OF_LINES = TIDBYT_CREDS.get("number_of_lines", 4)

IMG_WIDTH = 64
IMG_HEIGHT = 32

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TIDBYT_CREDS['tidbyt_key']}",
}


def always_datetime(d):
    return arrow.get(d.decoded("dtstart"))


def draw_week_ahead():
    img = Image.new("RGBA", (IMG_WIDTH, IMG_HEIGHT), color=(0, 0, 0, 0))
    d = ImageDraw.Draw(img)


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
