#!/usr/bin/env python

import argparse
from datetime import datetime, timezone, timedelta
import logging
import arrow

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
    durations = [60] * 10 + [100] * 3 + [125] + [175] + [6000]

    drawing_events = []
    for i, e in enumerate(events):
        drawing_events.append(e)

        if len(drawing_events) == utils.NUMBER_OF_LINES or i == len(events) - 1:
            # either we've got a screen-full of events or we've run out;
            # animate this...
            logging.debug(f"animating: {drawing_events}")
            for n in range(16):
                img = Image.new(
                    "RGBA", (utils.IMG_WIDTH, utils.IMG_HEIGHT), color=(0, 0, 0, 0)
                )
                d = ImageDraw.Draw(img)
                for p, e in enumerate(drawing_events):
                    d.text(
                        xy=(60 - n * 4, 8 * p),
                        text=e,
                        font=utils.FONT,
                        fill=(250, 250, 250),
                    )
                images.append(img)
            # ... and clear the drawing buffer
            drawing_events = []

    images[0].save(
        image_name,
        save_all=True,
        append_images=images[1:],
        optimize=False,
        duration=durations * (i + 1),
        loop=2,
    )

    return images


def fetch_events(hours=24):

    now = arrow.now()
    then = now + timedelta(hours=hours)

    all_events = []

    for cal in utils.TIDBYT_CREDS["calendars"]:
        all_events += utils.fetch_events(cal, now.datetime, then.datetime)

    # sort events by their starttime, coercing dates to datetimes
    all_events.sort(key=utils.always_datetime)
    logging.debug(all_events)
    return utils.make_printable_events(all_events)


def main():
    events = fetch_events(hours=args.hours)
    if events:
        logging.debug(f"posting events to Tidbyt at {utils.INSTALLATION_ID}")
        draw_push_in(events, utils.EVENTS_PIC)
        utils.post_image(utils.EVENTS_PIC, utils.INSTALLATION_ID)
    else:
        logging.debug("no events to post")
        utils.remove_installation(utils.INSTALLATION_ID)


if __name__ == "__main__":
    main()
