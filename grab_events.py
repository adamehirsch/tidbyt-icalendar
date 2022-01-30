#!/usr/bin/env python

import argparse
import base64
import datetime
import json
import logging

import requests
from PIL import Image, ImageDraw

import utils

parser = argparse.ArgumentParser()
parser.add_argument("--hours", type=int, default=24)
parser.add_argument("-d", "--debug", action="store_true", default=False)
args = parser.parse_args()

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=(logging.DEBUG if args.debug else logging.INFO),
)


def draw_push_in(events, image_name):
    # this function makes a splashy sidways-pull-in image
    images = []
    # the durations of the animation steps
    durations = [75] * 12 + [125] * 3 + [4000]

    drawing_events = []
    for i, e in enumerate(events):
        drawing_events.append(e)

        if len(drawing_events) == utils.NUMBER_OF_LINES or i == len(events) - 1:
            logging.debug(f"animating: {drawing_events}")
            for n in range(16):
                img = Image.new(
                    "RGBA", (utils.IMG_WIDTH, utils.IMG_HEIGHT), color=(0, 0, 0, 0)
                )
                d = ImageDraw.Draw(img)
                for p, e in enumerate(drawing_events):
                    d.text(
                        (60 - n * 4, 8 * p), e, font=utils.FONT, fill=(250, 250, 250)
                    )
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

    img = Image.new("RGBA", (utils.IMG_WIDTH, utils.IMG_HEIGHT), color=(0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    for i, e in enumerate(events):
        d.text((1, 1 + (7 * (i % 4))), e, font=utils.FONT, fill=(250, 250, 250))
        logging.debug(f"drawing at {1 + (7 * (i % 4))}: {e}")

        if (i + 1) % utils.NUMBER_OF_LINES == 0 or i == len(events) - 1:
            # drawn all the lines for one image; save this one and start a new image
            images.append(img)
            img = Image.new(
                "RGBA", (utils.IMG_WIDTH, utils.IMG_HEIGHT), color=(0, 0, 0, 0)
            )
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
                "installationID": utils.INSTALLATION_ID,
                "background": False,
            }
        )

        requests.request("POST", utils.PUSH_URL, data=payload, headers=utils.HEADERS)


def remove_installation(name):
    requests.request(
        "DELETE",
        f"https://api.tidbyt.com/v0/devices/{utils.DEVICE_ID}/installations/{name}",
        headers=utils.HEADERS,
    )


def fetch_events(hours=24):

    now = datetime.datetime.utcnow()
    then = now + datetime.timedelta(hours=hours)

    all_events = []

    for cal in utils.TIDBYT_CREDS["calendars"]:
        all_events += utils.fetch_events(cal, now, then)

    # sort events by their starttime, coercing dates to datetimes
    all_events.sort(key=utils.always_datetime)
    return utils.make_printable_events(all_events)


def main():
    events = fetch_events(hours=args.hours)
    if events:
        logging.debug("posting events to Tidbyt")
        # draw_image(events, EVENTS_PIC)
        draw_push_in(events, utils.EVENTS_PIC)
        post_image(utils.EVENTS_PIC)
    else:
        logging.debug("no events to post")
        remove_installation(utils.INSTALLATION_ID)


if __name__ == "__main__":
    main()
