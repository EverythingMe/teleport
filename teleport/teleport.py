import itertools
import random
import requests
import logging


registry = {}


class Plugin(type):
    def __new__(metacls, name, bases, namespace, **kwargs):
        cls = type.__new__(metacls, name, bases, dict(namespace))

        if hasattr(cls, "__provider_name__"):
            registry[cls.__provider_name__] = cls

        return cls


class TeleportationProvider(object):
    __metaclass__ = Plugin
    GEOIP_URL = 'http://geome-1042.appspot.com/'

    def __init__(self, name, countries, debug=False, **kwargs):
        self.name = name
        self.countries = countries
        self.debug = debug
        self.kwargs = kwargs

    def __repr__(self):
        return "{}: {}".format(self.__provider_name__, self.name)

    def can_teleport_to(self, place):
        return place in self.countries

    def teleport(self, place):
        """
        try teleporting
        """
        raise NotImplemented

    @property
    def is_proxy(self):
        return False

    def where_we_teleported(self):
        return requests.get(self.GEOIP_URL, proxies=self.get_proxies()).text.lower()

    def go_home(self):
        pass

    def get_proxies(self):
        return {}

    def get_peer_address(self):
        raise NotImplementedError


def _shuffle(i):
    i = list(i)
    random.shuffle(i)
    return i


def _construct(args):
    if args["type"] not in registry:
        raise RuntimeError("unsupported teleporation provider '{}'".format(args["type"]))

    return registry[args["type"]](**args)


class Teleport(object):
    def __init__(self, config):
        self.config = config

    def get_sorted_providers(self):
        by_priority = lambda provider: provider["priority"]
        sorted_by_priority = sorted(self.config["providers"], key=by_priority)
        grouped_by_priority = itertools.groupby(sorted_by_priority, key=by_priority)

        res = []

        for _, providers in grouped_by_priority:
            for args in _shuffle(providers):
                res.append(_construct(args))

        return res
        
    def who_can_teleport_to(self, place):
        return [
            provider for provider in self.get_sorted_providers()
            if provider.can_teleport_to(place)
        ]

    def goto(self, place):
        """
        If you want to go somewhere, goto is the best way to get there.
        
        - Ken Thompson
        """

        providers = self.who_can_teleport_to(place)

        if not providers:
            raise RuntimeError('no providers for "{}"'.format(place))

        logging.info('providers for %s: %s', place, providers)

        _errors = []

        for provider in providers:
            logging.info('trying provider: {}'.format(provider))

            try:
                if provider.teleport(place):
                    return provider

                logging.error('provider {} didn\'t work out, going home'.format(provider))
                provider.go_home()
            except Exception as e:
                logging.exception('provider %s failed', provider)
                _errors.append(e)

        raise RuntimeError('failed to teleport to "{}" (errors: {})'.format(place, _errors))
