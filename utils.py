import base64
import datetime
import json
import logging

import arrow
import recurring_ical_events
import requests
import yaml
from icalendar import Calendar
from PIL import Image, ImageDraw, ImageFont

with open("tidbyt.yaml") as f:
    TIDBYT_CREDS = yaml.load(f, Loader=yaml.FullLoader)


DEVICE_ID = TIDBYT_CREDS["tidbyt_id"]
INSTALLATION_ID = TIDBYT_CREDS["tidbyt_installation"]
LOCALTZ = TIDBYT_CREDS.get("timezone", "US/Central")

BASE_URL = f"https://api.tidbyt.com/v0/devices/{DEVICE_ID}"
LIST_URL = f"{BASE_URL}/installations"
PUSH_URL = f"{BASE_URL}/push"

# Filename to write the single animated events gif
EVENTS_PIC = "todays_events.gif"

FBCAL = TIDBYT_CREDS["freeBusyCal"]
FBCOLOR = TIDBYT_CREDS["freeBusyColor"]
FBINSTALL = TIDBYT_CREDS["freeBusyInstallation"]

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
        xpos = 2 + i * 9
        fill = "#FDF"
        if day == "S":
            # highlight the weekend days with a background color
            d.rectangle(xy=[xpos - 1, 0, xpos + 6, 7], fill="#187d27")
            fill = "#ddffe2"
        d.text(xy=(xpos, 0), text=day, font=this_font, fill=fill)
    return img


def fetch_events(calendar, start_time, end_time):
    logging.debug(f"==> checking calendar {calendar} from {start_time} to {end_time}")

    raw_cal = requests.get(calendar).text
    ical = Calendar.from_ical(raw_cal)
    events = recurring_ical_events.of(ical).between(start_time, end_time)
    events.sort(key=always_datetime)

    logging.debug(f" - adding {len(events)} events")
    for e in events:
        logging.debug(
            f"{e.decoded('dtstart')} {e.decoded('dtend')} "
            f"{e.decoded('summary').decode('utf-8')}"
        )
    return events


def get_event_times(e, day_start):
    shift_start = e.decoded("dtstart") - day_start
    shift_end = e.decoded("dtend") - day_start
    shift_duration = e.decoded("dtend") - e.decoded("dtstart")
    logging.debug(f"{shift_start} {shift_end} {shift_duration} {e.decoded('summary')}")
    return shift_start, shift_end, shift_duration


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
