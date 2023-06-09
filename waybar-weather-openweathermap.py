#!/usr/bin/env python

import json
import os
import sys
import time
import tomllib

import requests

config_file = os.path.join(
    os.environ.get("XDG_CONFIG_HOME"),
    "waybar/modules/custom-weather-openweathermap.toml",
)

with open(config_file, "rb") as t:
    config = tomllib.load(t)

params = {
    "appid": config["general"]["apikey"],
    "lang": config["general"]["lang"],
    "lat": config["location"]["lat"],
    "lon": config["location"]["lon"],
}

# https://openweathermap.org/api/one-call-api
response = requests.get(
    "https://api.openweathermap.org/data/2.5/onecall", params=params
)

# deserialize JSON
x = response.json()

# REQUIRED: icon font (Font-Awesome, Nerd-Fonts, Noto, etc.)
# info: https://openweathermap.org/weather-conditions#How-to-get-icon-URL
icons = config["icons"]


def format_wind_direction(deg):
    """
    format wind direction with N/S/W/E compass heading
    """

    cardinal = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    return cardinal[((int((float(deg) / 22.5) + 0.5)) % 16)]


def format_temp(temperature):
    """
    format OpenWeather temperature in Celsius
    """

    return (str(int(float(temperature) - 273.15)) + "°").ljust(4)


def sys_output(text, tooltip):
    """
    JSON-encode and print the output
    """

    sys.stdout.write(json.dumps({"text": text, "tooltip": tooltip.strip()}))
    sys.stdout.flush()


def main():
    """
    generate the weather text
    """

    current = x["current"]

    current["icon"] = current["weather"][0]["icon"]
    current["desc"] = current["weather"][0]["description"]
    current["timestamp"] = time.strftime("%T", time.localtime(int(current["dt"])))

    wind = {
        "deg": format_wind_direction(current["wind_deg"]),
        "speed": round(current["wind_speed"]),
    }

    # text (always visible)
    text = f"{icons[current['icon']]} {format_temp(current['temp'])}"

    # text (on hover)
    tooltip = "\n".join(
        (
            "<b>Now</b>",
            "---",
            "",
            f"{icons[current['icon']]} ({current['desc']})",
            "",
            f"Wind:  {wind['deg'] : <3} {wind['speed']} m/s",
            f"Feels: {format_temp(current['feels_like'])}",
            f"Humid: {current['humidity']}%",
            f"UV:    {current['uvi']}",
            "",
            "",
        )
    )

    for i, hour in zip(range(len(x["hourly"])), x["hourly"]):
        # skip the first entry (as its the current hour)
        # jump in +3h increments
        # skip anything beyond +12h
        if i < 1 or i % 3 or i > 12:
            continue

        hour["icon"] = hour["weather"][0]["icon"]
        hour["desc"] = hour["weather"][0]["description"]

        timestamp = time.strftime("%H:%M", time.localtime(hour["dt"]))

        temp = {"avg": format_temp(hour["temp"])}

        tooltip += "\n".join(
            (
                f"{timestamp} | {temp['avg'] : ^4} | {icons[hour['icon']]} ({hour['desc']})",
                "",
            )
        )

    tooltip += "\n"

    for i, day in zip(range(len(x["daily"])), x["daily"]):
        # select only today+3
        if i < 1 or i >= 4:
            continue

        day["icon"] = day["weather"][0]["icon"]
        day["desc"] = day["weather"][0]["description"]

        temp = {
            "min": format_temp(day["temp"]["min"]),
            "max": format_temp(day["temp"]["max"]),
        }

        timestamp = time.strftime("%a", time.localtime(int(day["dt"])))

        wind = {
            "dir": format_wind_direction(day["wind_deg"]),
            "speed": round(day["wind_speed"]),
        }

        tooltip += "\n".join(
            (
                f"<b>{timestamp}</b>",
                "---",
                "",
                f"{icons[day['icon']]} ({day['desc']})",
                "",
                f"Wind:  {wind['dir'] : <3} {wind['speed']} m/s",
                f"Temp:  {temp['min']} to {temp['max']}",
                f"Humid: {day['humidity']}%",
                f"UV:    {day['uvi']}",
                "",
                "",
            )
        )

    if "alerts" in x:
        # make sure the icon indicates an alert
        text += " ⚠️ "

        # add the actual alert content to the tooltip
        tooltip += "\n".join(
            (
                "<b>Alerts</b>",
                "---",
                "",
                "",
            )
        )

        for alert in x["alerts"]:
            start, stop = (
                time.strftime("%H:%M %a", time.localtime(alert["start"])),
                time.strftime("%H:%M %a", time.localtime(alert["end"])),
            )
            tooltip += "\n".join(
                (
                    f"<i>{start}</i> - <i>{stop}</i>",
                    "-",
                    "",
                    "" f"{alert['description']}",
                    "",
                    "",
                )
            )

    tooltip += "\n".join((f"<small>last update: {current['timestamp']}</small>", ""))

    sys_output(text, tooltip)


if __name__ == "__main__":
    main()
