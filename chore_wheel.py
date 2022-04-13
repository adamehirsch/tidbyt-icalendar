#!/usr/bin/env python

import argparse
import logging

import arrow
from PIL import Image, ImageDraw

import utils

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", action="store_true", default=False)
args = parser.parse_args()

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=(logging.DEBUG if args.debug else logging.INFO),
)

chore_config = utils.CHOREWHEEL
epoch = arrow.get("1970-01-01")
today = utils.NOW


def draw_chore_wheel(image_name, people, chores):
    images = []
    # the durations of the animation steps
    durations = [60] * 3 + [100] * 2 + [125] + [175] + [6000]

    drawing_people = []
    for i, person_name in enumerate(people):
        days = (epoch - today).days
        chore = chores[(days + i) % len(chores)]
        logging.debug(f"drawing {person_name} for {chore}")
        drawing_people.append((person_name, chore))

        if len(drawing_people) == utils.NUMBER_OF_LINES or i == len(people) - 1:
            # either we've got a screen-full of chores or we've run out;
            # animate this...
            logging.debug(f"animating: {drawing_people}")
            for n in range(8):
                img = Image.new(
                    "RGBA", (utils.IMG_WIDTH, utils.IMG_HEIGHT), color=(24, 0, 80, 0)
                )
                d = ImageDraw.Draw(img)
                for p, person_name in enumerate(drawing_people):
                    logging.debug(
                        f"{person_name} step: {n} y:{(32 - (n + 1) * 4)} + {(p * 8)}"
                    )
                    d.text(
                        xy=(1, (32 - (n + 1) * 4) + p * 8),
                        text=f"{person_name[0]}: {person_name[1]}",
                        font=utils.FONT,
                        fill=utils.DIVERGING_COLORS[p],
                    )
                images.append(img)
            # ... and clear the drawing buffer
            drawing_people = []

    images[0].save(
        image_name,
        save_all=True,
        append_images=images[1:],
        optimize=False,
        duration=durations * (i + 1),
        loop=2,
    )

    return images


def main():
    chore_image = "chorewheel.gif"
    chore_installation = chore_config.get("installation", "chore_wheel")
    if chore_config.get("people") and chore_config.get("chores"):
        logging.debug(f"posting chores to Tidbyt at {utils.INSTALLATION_ID}")
        draw_chore_wheel(chore_image, chore_config["people"], chore_config["chores"])
        utils.post_image(chore_image, chore_installation)
    else:
        logging.debug("no chores to post")
        utils.remove_installation(chore_installation)


if __name__ == "__main__":
    main()
