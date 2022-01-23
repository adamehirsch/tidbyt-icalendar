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
from PIL import Image, ImageDraw, ImageFont, ImageSequence

parser = argparse.ArgumentParser()
parser.add_argument("--hours", type=int, default=24)
parser.add_argument("-d", "--debug", action="store_true", default=False)
args = parser.parse_args()

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=(logging.DEBUG if args.debug else logging.INFO),
)

# the "tidbyt_creds.json" file includes some sensitive config variables:
#  - "tidbyt_installation" string (the installation ID for this app)
#  - "tidbyt_id" string (the ID for the target Tidbyt display)
#  - "tidbyt_key" string (the API key to auth for this Tidbyt)
#  - "calendars" a list of iCalendar URLs to poll for events

TC_FILE = open("tidybt_creds.json")
TIDBYT_CREDS = json.load(TC_FILE)

DEVICE_ID = TIDBYT_CREDS["tidbyt_id"]
INSTALLATION_ID = TIDBYT_CREDS["tidbyt_installation"]

BASE_URL = f"https://api.tidbyt.com/v0/devices/{DEVICE_ID}"
LIST_URL = f"{BASE_URL}/installations"
PUSH_URL = f"{BASE_URL}/push"

EVENTS_PIC = "todays_events.gif"
FONT_FILE = "fonts/4x6.pil"
FONT = ImageFont.load(FONT_FILE)

IMG_WIDTH = 64
IMG_HEIGHT = 32

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": TIDBYT_CREDS["tidbyt_key"],
}


def always_datetime(d):
    return arrow.get(d.decoded("dtstart"))


def draw_push_in(events, image_name):
    events_in_fours = make_event_fours(events)
    images = []

    durations = [75] * 12 + [125] * 3 + [4000]

    for i, four_events in enumerate(events_in_fours):
        for n in range(16):
            img = Image.new("RGBA", (IMG_WIDTH, IMG_HEIGHT), color=(0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            for p, e in enumerate(four_events):
                d.text((64 - n * 4, 1 + 7 * p), e, font=FONT, fill=(250, 250, 250))
            images.append(img)

    images[0].save(
        image_name,
        save_all=True,
        append_images=images[1:],
        optimize=False,
        duration=durations * (i + 1),
        loop=1,
    )

    return images


def make_event_fours(events):
    fours = []
    a = []
    # group events in quartets that fit on the screen
    for i, v in enumerate(events):
        logging.debug(f"{i} {v}")
        a.append(v)
        if ((i + 1) % 4 == 0) or i == len(events) - 1:
            fours.append(a)
            a = []
    return fours


def draw_image(events, image_name):

    images = []
    events_in_fours = make_event_fours(events)
    for i, four_events in enumerate(events_in_fours):
        logging.debug(f"making image {i} with {pformat(four_events)}")
        img = Image.new("RGBA", (IMG_WIDTH, IMG_HEIGHT), color=(0, 0, 0, 0))

        d = ImageDraw.Draw(img)
        i = 0
        for e in four_events:
            d.text((1, 1 + 7 * i), e, font=FONT, fill=(250, 250, 250))
            i += 1
        images.append(img)

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
