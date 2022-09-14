#!/usr/bin/env python

import argparse
import logging
import math

import arrow
from PIL import ImageDraw, ImageFont

import utils

FBCAL = utils.TIDBYT_CREDS["freebusy"]["calendars"]
FBCOLOR = utils.TIDBYT_CREDS["freebusy"]["color"]
FBINSTALL = utils.TIDBYT_CREDS["freebusy"]["installation"]
FBFONT = utils.TIDBYT_CREDS["freebusy"]["font"]

# Reads events from a single ical-format calendar and draw them as solid blocks of
# color on a 7-day x 24 hour calendar on the bottom 24 pixels of the display

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", action="store_true", default=False)
args = parser.parse_args()

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=(logging.DEBUG if args.debug else logging.INFO),
)


def get_next_event_duration(events, index, shift_end):
    if len(events) - 1 == index:
        return 0

    next_event = events[index + 1]
    next_start, _, next_duration = utils.get_event_times(
        next_event, day_start=arrow.now(utils.LOCALTZ).floor("day")
    )

    if shift_end == next_start:
        # the next shift starts immediately after the current one; sigh
        return next_duration.seconds // 3600
    return 0


def prev_event_adjacent(events, index):
    if index == 0:
        return False
    day_start = arrow.now(utils.LOCALTZ).floor("day")
    prev_event = events[index - 1]
    _, prev_end, _ = utils.get_event_times(prev_event, day_start)
    shift_start, _, _ = utils.get_event_times(events[index], day_start)
    return True if shift_start == prev_end else False


def draw_week_events(img, events, image_name):
    d = ImageDraw.Draw(img)
    teenyfont = ImageFont.load(FBFONT)

    day_start = arrow.now(utils.LOCALTZ).floor("day")

    for i, e in enumerate(events):
        shift_start, shift_end, shift_duration = utils.get_event_times(e, day_start)
        days_forward = shift_start.days

        # position the busy-blocks
        x_start = days_forward * 9 + 1
        x_end = x_start + 7

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
        # Don't insert it if the column starts too high (for a weirdly early shift start) or if there was an immediately preceding shift
        if y_start > 14 and not prev_event_adjacent(events, i):
            logging.debug(
                f"SHIFT DURATION: DAYS {shift_duration.days} SECONDS {shift_duration.seconds}"
            )

            hours_length = round(
                (shift_duration.days * 86400 + shift_duration.seconds) / 3600
            )
            # is there another event immediately after this one? Draw the total time.
            hours_length += get_next_event_duration(events, i, shift_end)

            text_x = x_start + (2 if hours_length < 10 else 0)
            text_y = y_start - 6

            logging.debug(
                f"text coords: {text_x} {text_y} length: {hours_length} "
                f"duration {shift_duration}"
            )

            # Only draw the hours-length if the pixel isn't already drawn on
            logging.debug(f"x, y: {(text_x, text_y)}")

            if img.getpixel((text_x, text_y)) != (0, 0, 0, 0):
                logging.debug("skipping drawing hours on populated pixel")
                continue

            d.text(
                xy=(
                    # center single digits over the column
                    text_x,
                    text_y,
                ),
                text=str(hours_length),
                font=teenyfont,
                fill="#fff",
            )

    img.save(image_name)


def main():
    fb_events = utils.fetch_events(
        FBCAL,
        arrow.now(utils.LOCALTZ).floor("day").datetime,
        arrow.now(utils.LOCALTZ).shift(days=6).ceil("day").datetime,
        skip_text=utils.TIDBYT_CREDS["freebusy"].get("skip_text", ""),
    )
    if fb_events:
        image_name = utils.TIDBYT_CREDS["freebusy"].get("image", "working.gif")
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
