import unittest
import responses
import logging

from threading import Thread
from tornado.ioloop import IOLoop
from tornado.gen import coroutine
from tornado.tcpserver import TCPServer
from mock import patch, MagicMock
from collections import defaultdict
from teleport import Teleport, TeleportationProvider, Luminati, OpenVPN

class ManagmentServer(TCPServer):
    SUCCESS_RESPONSE = [
        "Thu Jul 16 09:09:36 2015 MANAGEMENT: CMD 'state'\r\n",
        "1437037785,CONNECTED,SUCCESS,10.200.1.15,154.70.152.238\r\n",
        "END\r\n",
    ]

    WAITING_RESPONSE = [
        "Thu Jul 16 09:09:36 2015 MANAGEMENT: CMD 'state'\r\n",
        "1437037785,AUTH,,,\r\n",
        "END\r\n",
    ]

    BANNER = "INFO:OpenVPN Management Interface Version 1\r\n"

    def __init__(self, failing, *args, **kwargs):
        super(ManagmentServer, self).__init__(*args, **kwargs)

        self.failing = failing
        self.call_count = 0

    @coroutine
    def handle_stream(self, stream, address):
        yield stream.write(self.BANNER)

        line = yield stream.read_until("\n")

        if "state" in line:
            self.call_count += 1

            if not self.failing and self.call_count > 2:
                for line in self.SUCCESS_RESPONSE:
                    yield stream.write(line)
            else:
                for line in self.WAITING_RESPONSE:
                    yield stream.write(line)


class TeleportTestCase(unittest.TestCase):
    def setUp(self):
        class DummyTeleportationProvider(TeleportationProvider):
            __provider_name__ = "dummy_provider"

            @property
            def callCount(self):
                return self.__class__._counters[self.name]

            def teleport(self, place):
                self.__class__._counters[self.name] += 1

                if self.name.startswith("should_fail"):
                    return False

                return True

        # reset the counters for each test
        DummyTeleportationProvider._counters = defaultdict(int)

    def test_initialization_correct_order(self):
        config = {
            "providers": [
                { 
                    "name": "vova",
                    "type": "vpn",
                    "priority": 5,
                    "countries": [],
                    "params": {},
                },
                {
                    "name": "pita",
                    "type": "vpn",
                    "priority": 1,
                    "countries": [],
                    "params": {},
                },
                {
                    "name": "misha",
                    "type": "vpn",
                    "priority": 1,
                    "countries": [],
                    "params": {},
                },
                {
                    "name": "baba",
                    "type": "luminati",
                    "priority": 10,
                    "countries": [],
                    "username": "hey",
                    "password": "ho",
                }
            ]
        }

        teleport = Teleport(config)
        providers = teleport.get_sorted_providers()

        # pita and misha are highest priority so they
        # go first, the order between them is random
        # then vova, and finally baba

        names = [p.name for p in providers]
        expected_order_a = ["pita", "misha", "vova", "baba"] 
        expected_order_b = ["misha", "pita", "vova", "baba"]

        if names != expected_order_a and names != expected_order_b:
            self.fail("providers in incorrect order")

    def test_initializing_with_unsupported_provider(self):
        config = {
            "providers": [
                {
                    "name": "vova",
                    "type": "la la la",
                    "priority": 10,
                },
            ]
        }

        exceptionMessage = "unsupported teleporation provider 'la la la'"

        with self.assertRaisesRegexp(RuntimeError, exceptionMessage):
            Teleport(config).goto("hell")


    def assertProviders(self, teleport, place, expectedResults):
        self.assertEqual(
            [provider.name for provider in teleport.who_can_teleport_to(place)],
            expectedResults
        )

    def test_filtering_providers_that_cant_provide(self):
        config = {
            "providers": [
                { 
                    "name": "vova",
                    "type": "dummy_provider",
                    "priority": 5,
                    "countries": ["a", "b", "c"]
                },
                {
                    "name": "pita",
                    "type": "dummy_provider",
                    "priority": 1,
                    "countries": ["a", "b", "e"]
                },
                {
                    "name": "misha",
                    "type": "dummy_provider",
                    "priority": 1,
                    "countries": ["d"]
                },
            ]
        }

        teleport = Teleport(config)
        self.assertProviders(teleport, "a", ["pita", "vova"])
        self.assertProviders(teleport, "b", ["pita", "vova"])
        self.assertProviders(teleport, "c", ["vova"])
        self.assertProviders(teleport, "d", ["misha"])
        self.assertProviders(teleport, "e", ["pita"])
        self.assertProviders(teleport, "f", [])

    def test_try_teleporting_to_unteleportable_location(self):
        config = {
            "providers": [
                { 
                    "name": "vova",
                    "type": "dummy_provider",
                    "priority": 5,
                    "countries": ["a", "b", "c"]
                },
            ]
        }

        with self.assertRaisesRegexp(RuntimeError, "no providers for 'd'"):
            Teleport(config).goto("d")

    def test_trying_all_providers_before_giving_up(self):
        config = {
            "providers": [
                { 
                    "name": "should_fail_0",
                    "type": "dummy_provider",
                    "priority": 5,
                    "countries": ["a", "b", "c"]
                },
                {
                    "name": "should_fail_1",
                    "type": "dummy_provider",
                    "priority": 1,
                    "countries": ["a", "b", "e"]
                },
                {
                    "name": "should_fail_2",
                    "type": "dummy_provider",
                    "priority": 1,
                    "countries": ["a", "d"]
                },
            ]
        }

        teleport = Teleport(config)

        with self.assertRaisesRegexp(RuntimeError, "failed to teleport to 'a'"):
            teleport.goto("a")

        self.assertEqual(len(teleport.who_can_teleport_to("a")), 3)

        for provider in teleport.who_can_teleport_to("a"):
            self.assertEqual(provider.callCount, 1)

    def test_trying_all_providers_before_giving_up_with_retries(self):
        config = {
            "providers": [
                { 
                    "name": "should_fail_0",
                    "type": "dummy_provider",
                    "priority": 5,
                    "countries": ["a", "b", "c"]
                },
                {
                    "name": "should_fail_1",
                    "type": "dummy_provider",
                    "priority": 1,
                    "countries": ["a", "b", "e"]
                },
                {
                    "name": "should_fail_2",
                    "type": "dummy_provider",
                    "priority": 1,
                    "countries": ["a", "d"]
                },
            ]
        }

        teleport = Teleport(config)

        with self.assertRaisesRegexp(RuntimeError, "failed to teleport to 'a'"):
            teleport.goto("a")

        self.assertEqual(len(teleport.who_can_teleport_to("a")), 3)

        for provider in teleport.who_can_teleport_to("a"):
            self.assertEqual(provider.callCount, 1)

    def test_once_provider_connects_stop_trying_to_connect(self):
        config = {
            "providers": [
                { 
                    "name": "pita",
                    "type": "dummy_provider",
                    "priority": 5,
                    "countries": ["a"]
                },
                {
                    "name": "vova",
                    "type": "dummy_provider",
                    "priority": 2,
                    "countries": ["a"]
                },
                {
                    "name": "should_fail",
                    "type": "dummy_provider",
                    "priority": 1,
                    "countries": ["a"]
                },
            ]
        }

        teleport = Teleport(config)

        # shouldn't raise an exception
        provider = teleport.goto("a")

        providers = teleport.who_can_teleport_to("a")
        self.assertEqual(len(providers), 3)

        self.assertEqual(providers[0].callCount, 1)
        self.assertEqual(providers[1].callCount, 1)
        self.assertEqual(providers[2].callCount, 0)

        self.assertEqual(provider.name, "vova")


class TeleportationProviderTestCase(unittest.TestCase):
    def test_can_teleport_to(self):
        countries = ["a", "b", "c"]

        config = {
            "name": "vova",
            "countries": countries,
        }

        tp = TeleportationProvider(**config)

        for country in countries:
            self.assertTrue(tp.can_teleport_to(country))

        self.assertFalse(tp.can_teleport_to("vova"))
        self.assertFalse(tp.can_teleport_to("d"))


class LuminatiTestCase(unittest.TestCase):
    def setUp(self):
        config = {
            "name": "vova",
            "countries": [],
            "username": "vova",
            "password": "vova666kgb",
        }

        self.luminati = Luminati(**config)

    def test_getting_super_proxy(self):
        self.assertEqual(
            self.luminati.get_super_proxy_url(),
            "http://client.luminati.io/api/get_super_proxy?raw=1&user=vova&key=vova666kgb"
        )

    def test_get_proxy_auth(self):
        self.assertEqual(
            self.luminati.get_proxy_auth("VOVAVILLE"),
            "vova-country-VOVAVILLE:vova666kgb"
        )

    @responses.activate
    def test_get_proxy_address(self):
        fake_response = "100.64.0.1"
        expectedResult = "{}:22225".format(fake_response)

        responses.add(
            responses.GET,
            self.luminati.get_super_proxy_url(),
            status=200,
            body=fake_response,
            content_type="text/html",
            match_querystring=True
        )

        self.assertEqual(self.luminati.get_proxy_address(), expectedResult)

    @responses.activate
    def test_raises_error_when_failed_to_get_proxy_address(self):
        responses.add(
            responses.GET,
            self.luminati.get_super_proxy_url(),
            status=400,
            match_querystring=True,
            body="vova is sad",
        )

        exceptionMessage = "Luminati returned: 400: vova is sad"

        with self.assertRaisesRegexp(RuntimeError, exceptionMessage):
            self.luminati.get_proxy_address()

    @responses.activate
    def test_teleporting_to_a_wrong_place_should_return_false(self):
        fake_country_code = "XL"
        responses.add(
            responses.GET,
            'http://geome-1042.appspot.com/',
            status=200,
            body='{}'.format(fake_country_code),
            content_type="text/html",
        )

        responses.add(
            responses.GET,
            self.luminati.get_super_proxy_url(),
            status=200,
            body="100.64.1.5",
            content_type="text/html",
            match_querystring=True
        )

        self.assertFalse(self.luminati.teleport("be"))


class OpenVPNTestCase(unittest.TestCase):
    FREE_PORT = 12345

    def setUp(self):
        self.t = Thread(target=IOLoop.current().start)
        self.t.start()

    def tearDown(self):
        IOLoop.current().stop()

    @patch.object(OpenVPN, "_get_free_port", MagicMock(return_value=FREE_PORT))
    def test_crafting_openvpn_args(self):
        vpn = OpenVPN(
            binary="/usr/bin/openvpn",
            ca="hey.ca",
            key="hey.key",
            cert="hey.cert",
            host="vova.com",
            port=55669
        )

        expectedResults = [
            "/usr/bin/openvpn",
            "--management", "localhost", str(self.FREE_PORT),
            "--remote", "vova.com", "55669",

            "--client",
            "--route-metric", "1",
            "--ns-cert-type", "server",
            "--proto", "tcp",
            "--dev", "tun",
            "--resolv-retry", "infinite",
            "--ping-exit", "90",
            "--ca", "hey.ca",
            "--cert", "hey.cert",
            "--key", "hey.key",
        ]

        self.assertEqual(vpn.command(), expectedResults)

    def test_waiting_on_managment_port(self):
        server = ManagmentServer(failing=False)
        server.listen(55669)

        with patch.object(OpenVPN, "_get_free_port", MagicMock(return_value=55669)):
            vpn = OpenVPN(host="")
            self.assertTrue(vpn.wait_for_openvpn_to_connect(wait_between_retries=0.1))
            self.assertTrue(vpn.get_peer_address(), "154.70.152.238")

 
    def test_waiting_on_managment_port_failing(self):
        server = ManagmentServer(failing=True)
        server.listen(55667)

        with patch.object(OpenVPN, "_get_free_port", MagicMock(return_value=55667)):
            vpn = OpenVPN(host="")
            self.assertFalse(vpn.wait_for_openvpn_to_connect(wait_between_retries=0.1, retries=3))

    
    def test_kwargs_expanding(self):
        vpn = OpenVPN(
            host="",
            foo="",
            pita="pita_arg",
            baba="baba_arg",
        )

        self.assertEqual(
            vpn.expand_kwargs(),
            ["--baba", "baba_arg", "--pita", "pita_arg", "--foo"]
        )
