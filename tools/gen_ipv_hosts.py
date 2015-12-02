#!/usr/bin/env python

import zipfile
import yaml
import sys
import os
import requests
from collections import defaultdict
from StringIO import StringIO


IPV_CONFIG_URL = "https://www.ipvanish.com/software/configs/configs.zip"


def get_country_to_hosts(ipvanish_zip):
    res = defaultdict(list)

    for f in ipvanish_zip.namelist():
        if not f.endswith(".ovpn"):
            continue

        country_code = f.split("-")[1].lower()

        if country_code == 'uk':
            country_code = 'gb'

        ovpn = ipvanish_zip.open(f)

        for line in ovpn.readlines():
            if line.startswith("remote"):
                res[country_code].append(line.split(" ")[1])

    return dict(res)


def get_ipvanish_zip():
    zipdata = StringIO()
    zipdata.write(requests.get(IPV_CONFIG_URL).content)
    return zipfile.ZipFile(zipdata)


def main():
    print(yaml.dump(
        get_country_to_hosts(get_ipvanish_zip()),
        default_flow_style=False
    ))
    
if __name__ == "__main__":
    main()
