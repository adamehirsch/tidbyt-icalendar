#!/usr/bin/env python

import argparse
from datetime import datetime, timezone, timedelta
import logging
import arrow

from PIL import Image, ImageDraw

import utils

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=(logging.DEBUG if args.debug else logging.INFO),
)
