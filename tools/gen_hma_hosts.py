#!/usr/bin/env python
# -*- coding: utf-8 -*-


import requests
from collections import defaultdict
from geodis.countries import get2LetterCodeByName


HMA_HOSTS_URL = "https://www.hidemyass.com/vpn-config/l2tp/"
        
def get_hma_config():
    return requests.get(HMA_HOSTS_URL).text.split("\n")

normalized_countries = {
    "USA": "United States",
    "UK": "United Kingdom",
    "Republic of Singapore": "Singapore",
    "Brasil": "Brazil",
    "Luxembourg (LOC1 S1)": "Luxembourg",
    "Luxembourg (LOC1 S2)": "Luxembourg",
    "Luxembourg (LOC1 S3)": "Luxembourg",
    "Luxembourg (LOC1 S4)": "Luxembourg",
    "Luxembourg (LOC1 S5)": "Luxembourg",
    "Luxembourg (LOC1 S6)": "Luxembourg",
    "Luxembourg (LOC1 S7)": "Luxembourg",
    "Luxembourg (LOC1 S8)": "Luxembourg",
    "Palestine": "Israel",
    "Bosnia": "Bosnia and Herzegovina",
    "Cote d`Ivoire": "Ivory Coast",
    "Congo": "Republic of the Congo",
    "Macau": "Macao",
    "Pitcairn Islands": "Pitcairn",
    "Republic of Djibouti": "Djibouti",
}


def normalize_country(country):
    return normalized_countries.get(country, country)


def getAlpha2CountryCode(country):
    return get2LetterCodeByName(normalize_country(country)).lower()


def location_to_country_code(location):
    country = location.split(", ", 1)[0]
    return getAlpha2CountryCode(country)



def get_country_to_hosts():
    cc = defaultdict(list)

    for line in get_hma_config():
        host, location = line.split("\t")
        cc[location_to_country_code(location).lower()].append(str(host))

    return dict(cc)


def main():
    import yaml
    print(yaml.dump(get_country_to_hosts(), default_flow_style=False))



if __name__ == "__main__":
    main()
