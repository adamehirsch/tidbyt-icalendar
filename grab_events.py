#!/usr/bin/env python


import base64
import datetime
import json
import logging
import os.path
from pprint import pformat, pprint
import argparse
import arrow
import requests

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument("--hours", type=int, default=24)
parser.add_argument("-d", "--debug", action="store_true", default=False)
args = parser.parse_args()

TC_FILE = open("tidybt_creds.json")
TIDBYT_CREDS = json.load(TC_FILE)

DEVICE_ID = TIDBYT_CREDS["tidbyt_id"]

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=(logging.DEBUG if args.debug else logging.INFO),
)


BASE_URL = f"https://api.tidbyt.com/v0/devices/{DEVICE_ID}"
LIST_URL = f"{BASE_URL}/installations"
PUSH_URL = f"{BASE_URL}/push"

INSTALLATION_ID = TIDBYT_CREDS["tidbyt_installation"]
EVENTS_PIC = "todays_events.gif"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events.owned.readonly",
    "https://www.googleapis.com/auth/calendar.events.readonly",
]

CREDS_FILE = "creds.json"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": TIDBYT_CREDS["tidbyt_key"],
}


def draw_image(events, image_name):

    images = []
    width = 64
    height = 32

    fours = []
    a = []
    # group events in quartets
    for i, v in enumerate(events):
        logging.debug(f"{i} {v}")
        a.append(v)
        if (i and i % 4 == 0) or i == len(events) - 1:
            fours.append(a)
            a = []

    for i, four_events in enumerate(fours):
        logging.debug(f"making image {i} with {pformat(four_events)}")
        img = Image.new("RGB", (width, height), color=(0, 0, 0))
        fnt = ImageFont.load("fonts/4x6.pil")

        d = ImageDraw.Draw(img)
        i = 0
        for e in four_events:
            d.text((1, 2 + 7 * i), e, font=fnt, fill=(250, 250, 250))
            i += 1
        images.append(img)

    if images:
        logging.debug(f"saving image {image_name}")
        images[0].save(
            image_name,
            save_all=True,
            append_images=images[1:],
            optimize=False,
            duration=4000,
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


def get_credentials():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(CREDS_FILE):
        creds = Credentials.from_authorized_user_file(CREDS_FILE, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        logging.debug("no valid creds: refreshing")
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(CREDS_FILE, "w") as token:
            token.write(creds.to_json())
    return creds


def fetch_events(creds, hours=24):
    try:
        service = build("calendar", "v3", credentials=creds)

        # Call the Calendar API
        right_now = datetime.datetime.utcnow()
        now = right_now.isoformat() + "Z"  # 'Z' indicates UTC time
        twentyFourHours = (
            right_now + datetime.timedelta(hours=hours)
        ).isoformat() + "Z"  # 'Z' indicates UTC time

        printable_events = []

        for cal in TIDBYT_CREDS["calendars"]:
            logging.debug(f"==> checking calendar {cal}")
            events_result = (
                service.events()
                .list(
                    calendarId=cal,
                    timeMin=now,
                    timeMax=twentyFourHours,
                    # maxResults=10,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])
            # Prints the start and name of the next 10 events
            for event in events:
                # start = event["start"].get("dateTime", event["start"].get("date"))

                if start := event["start"].get("dateTime", ""):
                    suffix = "p"
                    if arrow.get(start).format("a") == "am":
                        suffix = "a"
                    hour = arrow.get(start).to("US/Central").format("h")

                    start = (
                        arrow.get(start).to("US/Central").format("hmm") + suffix + " "
                    )

                printable_events.append(f"{start}{event['summary']}")

        logging.debug(pformat(printable_events))
        return printable_events
    except HttpError as error:
        logging.error(f"An error occurred: {error}")
        return []


def main():
    creds = get_credentials()
    events = fetch_events(creds, hours=args.hours)
    if events:
        logging.debug("posting events to Tidbyt")
        draw_image(events, EVENTS_PIC)
        post_image(EVENTS_PIC)
    else:
        logging.debug("no events to post")
        remove_installation(INSTALLATION_ID)


def make_circles():
    # testing animated gif creation.
    images = []

    width = 64
    height = 32
    center = width // 2
    color_1 = (0, 0, 0)
    color_2 = (255, 255, 255)
    max_radius = int(center * 1.5)
    step = 8

    for i in range(0, max_radius, step):
        im = Image.new("RGB", (width, height), color_1)
        draw = ImageDraw.Draw(im)
        draw.ellipse((center - i, center - i, center + i, center + i), fill=color_2)
        images.append(im)

    for i in range(0, max_radius, step):
        im = Image.new("RGB", (width, height), color_2)
        draw = ImageDraw.Draw(im)
        draw.ellipse((center - i, center - i, center + i, center + i), fill=color_1)
        images.append(im)

    images[0].save(
        "pillow_imagedraw.gif",
        save_all=True,
        append_images=images[1:],
        optimize=False,
        duration=40,
        loop=0,
    )


if __name__ == "__main__":
    main()
    # make_circles()
    # post_image("pillow_imagedraw.gif")
