# ICS Calendar Events on a Tidbyt

I wanted to be able to put events from several of my family's shared calendars up on our Tidbyt, so I wrote a thing to do it. It polls a list of ICS (icalendar) files, figures out what events are coming up in the next N hours (defaulting to 24). It makes those events into an animated gif and sends it to your Tidbyt display using the official Tidbyt API. If there are no events, it removes itself from your display until the next time you run it and have something coming up.

## What you'll need

- a working python, version 3 or higher (virtualenv optional)
- the python modules listed in `requirements.txt` (i.e. `pip install -r requirements.txt`)
- a config/secrets file called `tidbyt.yaml`, with four values in it:
  - `tidbyt_installation`: the installation ID for the app you're installing, which can be any arbitrary string
  - `tidbyt_id`: the ID of your Tidbyt display, as acquired from your Tidbyt mobile app
  - `tidbyt_key`: the authentication key for your Tidbyt, also acquired from your Tidbyt mobile app
  - `calendars`: a list of URLs to ICS (iCalendar) records you'd like the script to look at when it runs

## Miscellaneous details

- misc fixed fonts from https://www.cl.cam.ac.uk/~mgk25/ucs-fonts.html, specifically at https://www.cl.cam.ac.uk/~mgk25/download/ucs-fonts.tar.gz
- I used `pilfont.py` as linked from https://pillow.readthedocs.io/en/stable/reference/ImageFont.html to convert the above fixed-width fonts into the format Pillow expects. I'm leaving the resulting image files here in the repo because
   - they were originally public-domain glyphs and
   - they're small
- I'm using the Tidbyt PUSH API endpoint as described here: https://tidbyt.dev/docs/tidbyt-api/b3A6MTYyODkwOA-push-to-a-device
  - The Tidbyt devs say this API is a work in progress, and make no commitments to its stability (totally appropriate at this phase of things) so caveat emptor. 
