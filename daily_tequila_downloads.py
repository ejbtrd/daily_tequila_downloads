#!/usr/bin/python3

# Downloads counter for tequilaOS
#
# Counts downloads for each device and sends
# them in telegram message every day

from pathlib import Path
from datetime import datetime
import asyncio
import json
import requests
import sys
import telegram

home = str(Path.home())

if len(sys.argv) > 1:
    BOT_TOKEN = sys.argv[1]
else:
    try:
        BOT_TOKEN = str(
            open(f"{home}/.config/tequilabottoken", "r").read().strip())
    except FileNotFoundError:
        sys.exit("github token not found")

CHAT_ID = -1001791062372

date = str(datetime.now().replace(second=0, microsecond=0))

diff = 0

skippeddevices = []

downloads = json.load(open("downloads.json", "r"))

try:
    GITHUB_TOKEN = str(open(f"{home}/.githubtoken", "r").read().strip())
    headers = {"Authorization": "Bearer " + GITHUB_TOKEN}
    GH_AUTH = True
except FileNotFoundError:
    GH_AUTH = False

devices_url = "https://raw.githubusercontent.com/tequilaOS/tequila_ota/main/devices.json"

response = requests.get(devices_url).json()


async def main():
    message = f"Download stats as of {date} in last 24 hours:\n"

    totalDownloads = 0
    totalPrevious = 0

    for oem in response:
        for device in response[oem]:
            deviceDownloads = 0

            oem = oem.lower()

            print(f"Processing {oem}/{device}...")
            url = f"https://api.github.com/repos/tequilaOS/platform_device_{oem}_{device}/releases"

            if GH_AUTH:
                deviceresponse = requests.get(url, headers=headers)
            else:
                deviceresponse = requests.get(url)

            if deviceresponse.status_code != 200:
                print(
                    f"Failed to get data for {device}!\n"
                    f"{deviceresponse.status_code}: {deviceresponse.text}"
                )
                skippeddevices.append(device)
                continue

            try:
                previous = downloads[device]
            except KeyError:
                downloads[device] = 0

            previous = downloads[device]

            if len(deviceresponse.json()) == 0:
                skippeddevices.append(device)
                continue

            for release in deviceresponse.json():
                for asset in release["assets"]:
                    print(f"  adding {asset['download_count']}")
                    deviceDownloads += asset["download_count"]

            downloads[device] = deviceDownloads

            totalDownloads += downloads[device]
            totalPrevious += previous

            diff = downloads[device] - previous

            downloads[device + "_diff"] = diff

            message += f"\n{device}: {deviceDownloads}"
            if diff != 0:
                message += f" (+{diff})"

    totalDiff = totalDownloads - totalPrevious

    message += "\n"
    message += "\n"

    if (len(skippeddevices) > 0):
        message += "Skipped devices:"

        for device in skippeddevices:
            message += f"\n{device}"

        message += "\n"
        message += "\n"

    message += f"Total: {totalDownloads}"
    if totalDiff != 0:
        message += f" (+{totalDiff})"

    print(message)

    # Send telegram message with results
    bot = telegram.Bot(BOT_TOKEN)
    async with bot:
        await bot.send_message(text=message, chat_id=CHAT_ID)

    downloads["_date"] = date

    downloads["_total"] = totalDownloads
    downloads["_total_diff"] = totalDiff

    # Write to JSON
    with open("downloads.json", "w") as f:
        f.write(json.dumps(downloads, indent=4, sort_keys=True))

if __name__ == '__main__':
    asyncio.run(main())
