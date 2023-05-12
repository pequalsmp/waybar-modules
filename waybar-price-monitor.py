#!/usr/bin/env python

import json
import os
import sys
import tomllib
import urllib.request

from lxml import html


class Pricing:
    """
    Provides methods to fetch, process, convert and normalize
    price for a given item, based on supported shop types.

    """

    def __init__(self, item):
        self.type = item["shop"]
        self.url = item["url"]

    def fetch(self):
        """
        fetch and process the prices for a given item

        Returns:

        list(old_price, new_price)

        """

        request = urllib.request.Request(self.url)
        request.add_header("Referer", self.url)
        request.add_header(
            "User-Agent",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36",
        )

        with urllib.request.urlopen(request) as response:
            self.data = response.read().decode("utf-8")

        return self

    def convert_price(self, price):
        """
        convert price if any other than BGN

        """

        if "€" in str(price):
            # fixed exchange - EURxBGN
            price = self.strip_price(price) * 1.95583
        else:
            price = self.strip_price(price)

        return float(f"{ float(price) :.2f}")

    def strip_price(self, price):
        """
        normalize/format price to a float with 2 decimal points

        """

        if isinstance(price, list):
            price = price[0]

        float_str = ""

        for i in price:
            if (ord(i) in range(48, 58)) or (ord(i) in (44, 46)):
                # subs (if needed)
                if ord(i) == 44:
                    # instead of dealing with locale (. vs ,)
                    float_str += chr(46)
                else:
                    float_str += i

        float_str = float_str.rstrip(".")

        return float(float_str)

    def process_data(self):
        """
        process the item, based on their shop type
        """

        tree = html.fromstring(self.data)

        if self.type == "modivo":
            data = self.modivo(tree)
        elif self.type == "obuvki":
            data = self.obuvki(tree)
        elif self.type == "reserved":
            data = self.reserved(tree)
        elif self.type == "tretorn":
            data = self.tretorn(tree)
        else:
            raise AttributeError("Invalid/Unsupported shop type")

        return list(map(self.convert_price, data))

    def modivo(self, html_str):
        """
        process html for items with shop type - modivo
        """

        final = html_str.xpath(
            '//article[@class="product"]//div[contains(@class, "final-price-wrapper")]//div[contains(@class, "price")]/text()'
        )
        regular = html_str.xpath(
            '//article[@class="product"]//div[contains(@class, "price-with-discount")]//div[contains(@class, "price")]/text()'
        )

        if len(regular) > 0:
            return (final, regular)

        return (final, final)

    def obuvki(self, html_str):
        """
        process html for items with shop type - obuvki
        """

        regular = html_str.xpath(
            '//div[contains(@class, "price-info")]/div/div[@class="price-with-discount"]/text()'
        )

        final = html_str.xpath(
            '//div[contains(@class, "price-info")]/div/div[contains(@class, "final-price")]/text()'
        )

        out_of_stock = html_str.xpath('//div[contains(@class, "out-of-stock-message")]')

        if len(out_of_stock) > 0:
            return (["0"], ["0"])

        if len(regular) > 0:
            return (final, regular)

        return (final, final)

    def reserved(self, html_str):
        """
        process html for items with shop type - reserved
        """

        scripts = html_str.xpath("//script/text()")

        for script in scripts:
            if ("gtmData" in script) and ("pageType" in script):
                json_open = script.find("{")
                json_close = script.find("}", json_open) + 1

                data = json.loads(script[json_open:json_close])

                return (data["price"], data["basePrice"])

        raise LookupError("Couldn't find data, maybe the page has been updated?")

    def tretorn(self, html_str):
        """
        process html for items with shop type - tretorn
        """

        price = html_str.xpath(
            '//div[@class="product-details"]//div[contains(@class, "price")]/text()'
        )

        if len(price) > 1:
            new = html_str.xpath(
                '//div[@class="product-details"]//div[contains(@class, "new-price")]/text()'
            )

            old = html_str.xpath(
                '//div[@class="product-details"]//div[contains(@class, "old-price")]/text()'
            )

            return (new, old)

        return (price, price)


def sys_output(data):
    """Format and print the collected data"""

    data.sort(key=lambda e: e["price"]["discount"])

    tooltips = []

    for item in data:
        tooltip = ""

        current, previous = [
            float(item["price"]["current"]),
            float(item["price"]["previous"]),
        ]

        tooltip += f"{ item['name'] : <30} | {item['shop'] : ^10} | { current : ^6} <sup>({previous : ^6})</sup>"

        if current < previous:
            tooltip += f" | { item['price']['discount'] :^8.2%}"
        else:
            tooltip += f" | { ' ' :<8}"

        # item is out of stock
        if current == 0.0 and previous == 0.0:
            tooltip = "<s>" + tooltip + "</s>"

        tooltip += "\n"

        tooltips.append(tooltip)

    out = {"tooltip": "".join(tooltips)}

    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()


def main():
    """main function, fetch prices and JSON-encode"""
    data = []

    items_file = os.path.join(
        os.environ.get("XDG_CONFIG_HOME"),
        "waybar/modules/custom-price-monitor.toml",
    )

    with open(items_file, "rb") as t:
        items = tomllib.load(t)

    for item in items:
        current_price, previous_price = list(
            map(float, Pricing(item).fetch().process_data())
        )

        if current_price != previous_price:
            discount = (current_price - previous_price) / previous_price
        else:
            discount = 0

        data.append(
            {
                "name": item["name"],
                "shop": item["shop"],
                "price": {
                    "current": current_price,
                    "previous": previous_price,
                    "discount": discount,
                },
            }
        )

    sys_output(data)


if __name__ == "__main__":
    main()
