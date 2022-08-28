#!/usr/bin/python3

# Downloads counter for tequilaOS
#
# Counts downloads for each device and sends
# them in telegram message every day

from pathlib import Path
from datetime import datetime
import json
import requests
import sys
import telegram

home = str(Path.home())

if len(sys.argv) > 1:
    BOT_TOKEN = sys.argv[1]
else:
    try:
        BOT_TOKEN = str(open(home + "/.config/tequilabottoken", "r").read().strip())
    except FileNotFoundError:
        sys.exit("github token not found")

CHAT_ID = -1001791062372

BRANCH = "tobacco"

date = str(datetime.now().replace(second=0, microsecond=0))

message = "Download stats as of " + date + " in last 24 hours:\n"

totalDownloads = 0
totalPrevious = 0

diff = 0

skippeddevices = []

downloads = json.load(open("downloads.json", "r"))

devices_url = "https://raw.githubusercontent.com/tequilaOS/tequila_ota/sombrero/devices.json"

response = requests.get(devices_url).json()

for oem in response:
    for device in response[oem]:
        deviceDownloads = 0

        oem = oem.lower()

        print("Processing " + oem + "/" + device + "...")
        url = "https://api.github.com/repos/tequilaOS/platform_device_" + oem + "_" + device + "/releases"

        deviceresponse = requests.get(url)

        if deviceresponse.status_code != 200:
            skippeddevices.append(device)
            continue

        try:
            previous = downloads[device]
        except KeyError:
            downloads[device] = 0

        previous = downloads[device]

        for release in deviceresponse.json():
            if release["prerelease"]:
                # Skip release if prerelease is "true" (experimental build)
                continue

            for asset in release["assets"]:
                if BRANCH not in asset["name"]:
                    continue

                print("  adding " + str(asset["download_count"]))
                deviceDownloads += asset["download_count"]

        downloads[device] = deviceDownloads

        totalDownloads += downloads[device]
        totalPrevious += previous

        diff = downloads[device] - previous

        message += "\n" + device + ": " + str(deviceDownloads)
        if diff != 0:
            message += " (+" + str(diff) + ")"

totalDiff = totalDownloads - totalPrevious

message += "\n"
message += "\n"

if (len(skippeddevices) > 0):
    message += "Skipped devices:"

    for device in skippeddevices:
        message += "\n" + device

    message += "\n"
    message += "\n"

message += "Total: " + str(totalDownloads)
if diff != 0:
    message += " (+" + str(totalDiff) + ")"

print(message)
# Send telegram message with results
bot = telegram.Bot(token=BOT_TOKEN)
bot.send_message(text=message, chat_id=CHAT_ID)

# Write to JSON
with open("downloads.json", "w") as f:
    f.write(json.dumps(downloads, indent=4))
