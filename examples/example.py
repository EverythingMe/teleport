#!/usr/bin/env python

import click
import yaml
import os
from teleport import Teleporter

__author__ = 'quatrix'


def setup_yaml(root):
    def include(loader, node):
        """Include another YAML file."""

        filename = os.path.join(root, loader.construct_scalar(node))
        data = yaml.load(open(filename, 'r'))
        return data

    yaml.add_constructor('!include', include)


def do_stuff(proxy, proxy_auth):
    """
    do something with in the context of a country
    proxy and proxy_auth provided in case they're needed to be passed
    to a http client like requests
    """
    pass


@click.command()
@click.option('--country', required=True, help='two letter country code')
@click.option('--config', required=True, type=click.File('rb'), help='teleportation provider config file')
@click.option('--dns-servers', default='8.8.8.8', help='comman seperated list of dns servers')
def main(country, config, dns_servers):
    setup_yaml(os.path.dirname(config.name))
    config = yaml.load(config.read())

    with Teleporter(config, country, dns_servers=dns_servers) as t:
        proxy = ''
        proxy_auth = ''

        if t.is_proxy:
            proxy = t.get_proxy_address()
            proxy_auth = t.get_proxy_auth(country)

        do_stuff(proxy, proxy_auth)

if __name__ == '__main__':
    main()
