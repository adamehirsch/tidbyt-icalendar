# ICS Calendar Events on a Tidbyt

I wanted to be able to put events from several of my family's shared calendars up on our Tidbyt, so I wrote a thing to do it. It polls a list of ICS (icalendar) files, figures out what events are coming up in the next N hours (defaulting to 24). It makes those events into an animated gif and sends it to your Tidbyt display using the official Tidbyt API. If there are no events, it removes itself from your display until the next time you run it and have something coming up.

## What you'll need

- a working python, version 3.9 or higher (specified in python-poetry)
- the python modules listed in pyproject.toml (I'm using python-poetry)
- a config/secrets file called `tidbyt.yaml`, with the following values in it:
  - `tidbyt_installation`: the installation ID for the app you're installing, which can be any arbitrary string
  - `tidbyt_id`: the ID of your Tidbyt display, as acquired from your Tidbyt mobile app
  - `tidbyt_key`: the authentication key for your Tidbyt, also acquired from your Tidbyt mobile app
  - `font`: (defaults to `fonts/4x6.pil`) path to the font to use while drawing the images
  - `number_of_lines`: (defaults to `4`) how many lines of teeny text to put on the images
  - `calendars`: a list of URLs to ICS (iCalendar) records you'd like the script to look at when it runs
    - If you're using Google Calendar, you'll find that individual calendars have a settings value called "Secret Address in iCal format" -- that's what I'm using here.

## How to use it

Run `grab_events.py`. Optionally add a `--hours N` argument, where `N` is the number of hours in the future to look ahead for events. If all goes well, the script will fetch down your events, sort them chronologically, and put some animated gifs on your Tidbyt rotation. If you want to test it and have no events in the next 24 hours, try running it with a longer duration to pick up more events.

I run it at 6 a.m. and 6 p.m. local time, from a cron job. That way when my
family sits to dinner, we can see upcoming events.

## Miscellaneous details

- misc fixed fonts came from https://www.cl.cam.ac.uk/~mgk25/ucs-fonts.html, specifically at https://www.cl.cam.ac.uk/~mgk25/download/ucs-fonts.tar.gz
- I used `pilfont.py` as linked from https://pillow.readthedocs.io/en/stable/reference/ImageFont.html to convert the above fixed-width fonts into the format Pillow expects. I'm leaving the resulting image files here in the repo under `fonts` because
   - they were originally public-domain glyphs and
   - they're small, so I don't mind putting them in source control.
- I'm using the Tidbyt PUSH API endpoint as described here: https://tidbyt.dev/docs/tidbyt-api/b3A6MTYyODkwOA-push-to-a-device
  - The Tidbyt devs say this API is a work in progress, and make no commitments to its stability (totally appropriate at this phase of things) so caveat emptor. 
- The icalevents library needs both a very specific fix version (specified in pyproject.toml) and a minor file update as specified at https://github.com/Herrner/icalevents/pull/2/files -- surely there must be a better way.
