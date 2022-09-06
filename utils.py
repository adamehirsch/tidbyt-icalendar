import base64
import datetime
import json
import logging
import re

import arrow
import requests
import yaml
import pytz
from PIL import Image, ImageDraw, ImageFont

from icalevents.icalevents import events
from pprint import pformat

with open("tidbyt.yaml") as f:
    TIDBYT_CREDS = yaml.load(f, Loader=yaml.FullLoader)


DEVICE_ID = TIDBYT_CREDS["tidbyt_id"]
INSTALLATION_ID = TIDBYT_CREDS["tidbyt_installation"]
LOCALTZ = TIDBYT_CREDS.get("timezone", "US/Central")
local_timezone = pytz.timezone(LOCALTZ)


CHOREWHEEL = TIDBYT_CREDS.get("chore_wheel", None)


BASE_URL = f"https://api.tidbyt.com/v0/devices/{DEVICE_ID}"
LIST_URL = f"{BASE_URL}/installations"
PUSH_URL = f"{BASE_URL}/push"

# Filename to write the single animated events gif
EVENTS_PIC = "todays_events.gif"

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
NOW = arrow.utcnow().to(TIDBYT_CREDS.get("timezone", "US/Central"))

DIVERGING_COLORS = [
    (127, 201, 127),
    (190, 174, 212),
    (253, 192, 134),
    (255, 255, 153),
    (56, 108, 176),
    (240, 2, 127),
    (191, 91, 23),
    (102, 102, 102),
]


def always_datetime(d):
    return arrow.get(d.start)


def draw_week_ahead():
    img = Image.new("RGBA", (IMG_WIDTH, IMG_HEIGHT))
    d = ImageDraw.Draw(img)
    this_font = ImageFont.load("fonts/6x9.pil")

    for i in range(7):
        day_of_week = arrow.utcnow().shift(days=i).to("US/Central").format("d")
        day = WEEKDAYS[day_of_week]
        xpos = 2 + i * 9
        fill = "#FDF"
        if day == "S":
            # highlight the weekend days with a background color
            d.rectangle(xy=[xpos - 1, 0, xpos + 6, 7], fill="#187d27")
            fill = "#ddffe2"
        d.text(xy=(xpos, 0), text=day, font=this_font, fill=fill)
    return img


def fetch_events(calendar, start_time, end_time, skip_text=""):
    logging.debug(f"==> checking calendar {calendar} from {start_time} to {end_time}")

    all_events = events(calendar, start=start_time, end=end_time)
    logging.debug(f"EVENTS: {all_events}")

    if skip_text:
        logging.debug(f"Knocking out events with text '{skip_text}'")
        all_events = list(
            filter(
                lambda e: (
                    not re.search(skip_text, str(e.summary), re.IGNORECASE)
                    or re.search(skip_text, str(e.description), re.IGNORECASE)
                ),
                all_events,
            )
        )

    for e in all_events:
        # This is a dippy workaround for a scheduling thing from QGenda, bah,
        # in which they record an overnight shift as an all_day event. Come on, folks.
        if e.all_day:
            e.start = local_timezone.localize(
                datetime.datetime(e.start.year, e.start.month, e.start.day, 16, 30, 0)
            )
            e.end = local_timezone.localize(
                datetime.datetime(e.end.year, e.end.month, e.end.day, 7, 0, 0)
            )
            e.all_day = False
            logging.debug(f"ALL DAY event becomes {e.start} {e.end}")

    logging.debug(f" - adding {len(all_events)} events")
    for e in all_events:
        logging.debug(f"{e.start} {e.end} " f"{e.description}")
    return all_events


def get_event_times(e, day_start):
    logging.debug(f"{e.start} {e.end} {day_start}")
    shift_start = e.start - day_start
    shift_end = e.end - day_start
    shift_duration = e.end - e.start
    logging.debug(f"{shift_start} {shift_end} {shift_duration} {e.description}")
    return shift_start, shift_end, shift_duration


def make_printable_events(events):
    printable_events = []
    for event in events:
        summary = event.summary

        start = event.start
        duration = event.end - event.start
        starttime = ""
        # this is a clunky way of differentiating all-day events from ones with hours
        if duration.total_seconds() < 86400:
            starthour = (
                arrow.get(start).to(LOCALTZ).format("h")
                if isinstance(start, datetime.datetime)
                else arrow.get(start).format("h")
            )
            sm = arrow.get(start).to(LOCALTZ).format("mm")
            startminute = "" if sm == "00" else sm

            suffix = "p"
            if arrow.get(start).to(LOCALTZ).format("a") == "am":
                suffix = "a"
            starttime += starthour + startminute + suffix + " "
        printable_line = f"{starttime}{summary}"
        logging.debug(f" - Adding event {printable_line}")
        printable_events.append(printable_line)
    return printable_events


def post_image(image_name, installation_id):

    with open(image_name, "rb") as open_file:
        byte_content = open_file.read()

        payload = json.dumps(
            {
                "image": base64.b64encode(byte_content).decode("utf-8"),
                "installationID": installation_id,
                "background": False,
            }
        )

        requests.request("POST", PUSH_URL, data=payload, headers=HEADERS)


def remove_installation(name):
    requests.request(
        "DELETE",
        f"https://api.tidbyt.com/v0/devices/{DEVICE_ID}/installations/{name}",
        headers=HEADERS,
    )
