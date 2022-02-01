#!/usr/bin/env python

import argparse
import logging

import arrow
from PIL import ImageDraw, ImageFont

import utils

FBCAL = utils.TIDBYT_CREDS["freeBusyCal"]
FBCOLOR = utils.TIDBYT_CREDS["freeBusyColor"]
FBINSTALL = utils.TIDBYT_CREDS["freeBusyInstallation"]

# Meant to read events from one calendar and draw them as solid blocks of
# color on a 7-day x 24 hour calendar on the bottom 24 pixels of the display

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", action="store_true", default=False)
args = parser.parse_args()

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=(logging.DEBUG if args.debug else logging.INFO),
)


def draw_week_events(img, events, image_name):
    d = ImageDraw.Draw(img)
    teenyfont = ImageFont.load("fonts/4x6.pil")

    tf = arrow.now(utils.LOCALTZ).floor("day")

    for e in events:
        shift_start = e.decoded("dtstart") - tf
        shift_end = e.decoded("dtend") - tf

        shift_duration = e.decoded("dtend") - e.decoded("dtstart")

        days_forward = shift_start.days
        if days_forward > 6:
            continue
        x_start = days_forward * 9
        x_end = x_start + 6

        hour_start = shift_start.seconds // 3600
        hour_end = shift_end.seconds // 3600
        y_start = 8 + hour_start
        y_end = 8 + hour_end

        if shift_start.days == shift_end.days:
            # this is a same-day shift; one rectangle
            d.rectangle([x_start, y_start, x_end, y_end], fill=FBCOLOR)
        else:
            # draw a rectangle to finish the day
            d.rectangle([x_start, y_start, x_end, 32], fill=FBCOLOR)
            # and another at the top of the next day, unless it's the last day
            if shift_end.days < 7:
                d.rectangle([x_start + 9, 8, x_end + 9, y_end], fill=FBCOLOR)
        # this is meant to put the length of the shift above the block.
        # Don't insert it if the column starts too high (for a weirdly early shift start)
        if y_start > 14:
            d.text(
                xy=(
                    # center single digits over the column
                    x_start + (2 if (shift_duration.seconds // 3600) < 10 else 0),
                    y_start - 6,
                ),
                text=str(shift_duration.seconds // 3600),
                font=teenyfont,
                fill="#fff",
            )
    img.save(image_name)


def main():
    fb_events = utils.fetch_events(FBCAL, arrow.utcnow(), arrow.utcnow().shift(days=7))
    if fb_events:
        image_name = utils.TIDBYT_CREDS.get("freeBusyImage", "working.gif")
        logging.debug("posting events to Tidbyt")
        week_image = utils.draw_week_ahead()
        draw_week_events(
            week_image,
            fb_events,
            image_name,
        )
        utils.post_image(image_name, FBINSTALL)
    else:
        logging.debug("no events to post")
        utils.remove_installation(FBINSTALL)


if __name__ == "__main__":
    main()
