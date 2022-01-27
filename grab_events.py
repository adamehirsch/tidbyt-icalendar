#!/usr/bin/env python


import argparse
import base64
import datetime
import json
import logging
from pprint import pformat

import arrow
import recurring_ical_events
import requests
from icalendar import Calendar
from PIL import Image, ImageDraw, ImageFont
import yaml

parser = argparse.ArgumentParser()
parser.add_argument("--hours", type=int, default=24)
parser.add_argument("-d", "--debug", action="store_true", default=False)
args = parser.parse_args()

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=(logging.DEBUG if args.debug else logging.INFO),
)

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


def draw_push_in(events, image_name):
    # this function makes a splashy sidways-pull-in image
    images = []
    # the durations of the animation steps
    durations = [75] * 12 + [125] * 3 + [4000]

    drawing_events = []
    for i, e in enumerate(events):
        drawing_events.append(e)

        if len(drawing_events) == NUMBER_OF_LINES or i == len(events) - 1:
            logging.debug(f"animating: {drawing_events}")
            for n in range(16):
                img = Image.new("RGBA", (IMG_WIDTH, IMG_HEIGHT), color=(0, 0, 0, 0))
                d = ImageDraw.Draw(img)
                for p, e in enumerate(drawing_events):
                    d.text((60 - n * 4, 8 * p), e, font=FONT, fill=(250, 250, 250))
                images.append(img)
            drawing_events = []

    images[0].save(
        image_name,
        save_all=True,
        append_images=images[1:],
        optimize=False,
        duration=durations * (i + 1),
        loop=1,
    )

    return images


def draw_image(events, image_name):
    # this function makes a simple flash-through image
    images = []

    img = Image.new("RGBA", (IMG_WIDTH, IMG_HEIGHT), color=(0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    for i, e in enumerate(events):
        d.text((1, 1 + (7 * (i % 4))), e, font=FONT, fill=(250, 250, 250))
        logging.debug(f"drawing at {1 + (7 * (i % 4))}: {e}")

        if (i + 1) % NUMBER_OF_LINES == 0 or i == len(events) - 1:
            # drawn all the lines for one image; save this one and start a new image
            images.append(img)
            img = Image.new("RGBA", (IMG_WIDTH, IMG_HEIGHT), color=(0, 0, 0, 0))
            d = ImageDraw.Draw(img)

    if images:
        logging.debug(f"saving image {image_name}")
        images[0].save(
            image_name,
            save_all=True,
            append_images=images[1:],
            optimize=False,
            duration=3000,
            loop=0,
        )


def post_image(image_name):

    with open(image_name, "rb") as open_file:
        byte_content = open_file.read()

        payload = json.dumps(
            {
                "image": base64.b64encode(byte_content).decode("utf-8"),
                "installationID": INSTALLATION_ID,
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


def fetch_events(hours=24):

    now = datetime.datetime.utcnow()
    then = now + datetime.timedelta(hours=hours)

    all_events = []
    printable_events = []

    for cal in TIDBYT_CREDS["calendars"]:

        logging.debug(f"==> checking calendar {cal}")

        raw_cal = requests.get(cal).text
        ical = Calendar.from_ical(raw_cal)
        events = recurring_ical_events.of(ical).between(now.date(), then.date())

        logging.debug(f" - adding {len(events)} events")
        all_events += events

    # sort events by their starttime, coercing dates to datetimes
    all_events.sort(key=always_datetime)

    for event in all_events:
        summary = event.decoded("summary").decode("utf-8")

        start = event["DTSTART"].dt
        duration = event["DTEND"].dt - event["DTSTART"].dt

        starttime = ""
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

    logging.debug(pformat(printable_events))
    return printable_events


def main():
    events = fetch_events(hours=args.hours)
    if events:
        logging.debug("posting events to Tidbyt")
        # draw_image(events, EVENTS_PIC)
        draw_push_in(events, EVENTS_PIC)
        post_image(EVENTS_PIC)
    else:
        logging.debug("no events to post")
        remove_installation(INSTALLATION_ID)


if __name__ == "__main__":
    main()
