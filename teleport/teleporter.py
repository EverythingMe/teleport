from teleport import Teleport
import logging
from contextlib import contextmanager
from subprocess import check_call


def _run_commands(commands):
    for command in commands:
        logging.debug("running command '%s'", " ".join(command))
        check_call(command)


def allow_traffic_only_to(address, dns_servers=None):
    host = address.split(":")[0]
    logging.info("Allowing traffic only to %s on eth0", host)

    commands = [
        ["iptables", "-A", "OUTPUT", "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"],
        ["iptables", "-A", "OUTPUT", "-o", "tun0", "-j", "ACCEPT"],
        ["iptables", "-A", "OUTPUT", "-o", "lo", "-j", "ACCEPT"],
        ["iptables", "-A", "OUTPUT", "-o", "eth0", "-d", host, "-j", "ACCEPT"],
        ["iptables", "-P", "OUTPUT", "DROP"],
    ]

    if dns_servers is not None:
        logging.info('Allowing traffic to dns servers %s', dns_servers)

        for dns_server in dns_servers:
            commands.append(["iptables", "-A", "OUTPUT", "-o", "eth0", "-d", dns_server, "-j", "ACCEPT"])

    _run_commands(commands)


def reset_firewall():
    logging.info("resetting firewall")

    commands = [
        ["iptables", "-F"],
        ["iptables", "-P", "OUTPUT", "ACCEPT"],
    ]

    _run_commands(commands)


@contextmanager
def FirewallContext(address, dns_servers=None):
    allow_traffic_only_to(address, dns_servers)

    try:
        yield
    finally:
        reset_firewall()


@contextmanager
def Teleporter(config, place, with_firewall=True, dns_servers=None):
    t = Teleport(config).goto(place)
    
    try:
        if with_firewall:
            with FirewallContext(t.get_peer_address(), dns_servers=dns_servers):
                yield t
        else:
            yield t
    finally:
        t.go_home()
