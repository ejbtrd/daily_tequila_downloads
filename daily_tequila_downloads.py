#!/usr/bin/env python

# Downloads counter for tequilaOS
#
# Counts downloads for each device and sends
# them in telegram message every day

from datetime import datetime
from dotenv import load_dotenv

import asyncio
import json
import os
import requests
import telegram


async def main():
    load_dotenv("config.env")

    TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
    CHAT_ID = -1001791062372

    date = str(datetime.now().replace(second=0, microsecond=0))

    totalDownloads = totalPrevious = diff = 0

    skippeddevices = []

    downloads = json.load(open("downloads.json", "r"))

    devices_url = "https://raw.githubusercontent.com/tequilaOS/tequila_ota/main/devices.json"

    response = requests.get(devices_url).json()

    message = f"Download stats as of {date} in last 24 hours:\n"

    for oem in response:
        for device in response[oem]:
            deviceDownloads = 0

            oem = oem.lower()

            print(f"Processing {oem}/{device}...")

            url = f"https://api.github.com/repos/tequilaOS/platform_device_{oem}_{device}/releases"
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
            finally:
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
    bot = telegram.Bot(TG_BOT_TOKEN)
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
