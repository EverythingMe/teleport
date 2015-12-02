import os
import random
import subprocess
import socket
import logging
import itertools
import time
import errno

from teleport import TeleportationProvider


class TimeoutPopen(subprocess.Popen):
    def wait(self, timeout=None):
        """Wait for child process to terminate.  Returns returncode
        attribute."""
        start = time.time()

        while self.returncode is None and (timeout is None or time.time() - start < timeout):
            try:
                pid, sts = subprocess._eintr_retry_call(os.waitpid, self.pid, os.WNOHANG)

                # WNOHANG in action!
                if pid == 0:
                    time.sleep(0.1)

                    continue
            except OSError as e:
                if e.errno != errno.ECHILD:
                    raise

                # This happens if SIGCLD is set to be ignored or waiting
                # for child processes has otherwise been disabled for our
                # process.  This child is dead, we can't get the status.
                pid = self.pid
                sts = 0

            # Check the pid and loop as waitpid has been known to return
            # 0 even without WNOHANG in odd situations.  issue14396.
            if pid == self.pid:
                self._handle_exitstatus(sts)

        return self.returncode


class OpenVPNManagmentContext(object):
    OPENVPN_BANNER = "INFO:OpenVPN Management Interface Version 1"
    SUCCESS_RESPONSE = "CONNECTED,SUCCESS"


    def __init__(self, host, port, timeout):
        self._host = host
        self._port = port
        self._timeout = timeout

    def __enter__(self):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(self._timeout)
        client.connect((self._host, self._port))
        self._client = client

        self.validate_banner()

        return self

    def validate_banner(self):
        banner = self._client.recv(1024)

        if self.OPENVPN_BANNER not in banner:
            raise Exception("openvpn banner not found, got: '{}'".format(banner))

    def get_peer_ip(self):
        self._client.sendall("state\r\n")

        while True:
            for line in self._client.recv(1024).split("\n"):
                logging.debug("line: %s", line)
                if self.SUCCESS_RESPONSE in line:
                    self._vpn_ip = line.split(",")[-1].strip()
                elif "END" in line:
                    return getattr(self, "_vpn_ip", None)

    def __exit__(self, type, value, traceback):
        self._client.close()


class OpenVPN(object):
    DEFAULT_FLAGS = [
        "--client",
        "--route-metric", "1",
        "--ns-cert-type", "server",
        "--proto", "tcp",
        "--dev", "tun",
        "--resolv-retry", "infinite",
        "--ping-exit", "90",
    ]

    def __init__(self, host, binary="openvpn", port=443, debug=False, vpn_termination_timeout=30, **kwargs):
        logging.info("trying to connect to vpn server %s", host)
        self.binary = binary
        self.host = host
        self.port = port
        self.debug = debug
        self.vpn_termination_timeout = vpn_termination_timeout

        tls_remote = kwargs.pop("tls-remote", None)

        if tls_remote:
            kwargs["tls-remote"] = host

        self.kwargs = kwargs

    @staticmethod
    def _get_free_port():
        s = socket.socket()
        s.bind(('', 0))
        port = s.getsockname()[-1]
        s.close()
        return port

    @property
    def management_port(self):
        if not hasattr(self, "_port"):
            self._port = self._get_free_port()
        return self._port

    def expand_kwargs(self):
        res = itertools.chain.from_iterable([
            ["--{}".format(k), v]
            for k, v in self.kwargs.iteritems()
        ])

        return [str(i) for i in res if i != ""]

    def command(self):
        ret = [
            self.binary,
            "--management", "localhost", str(self.management_port),
            "--remote", self.host, str(self.port),
        ] + self.DEFAULT_FLAGS

        ret = ret + self.expand_kwargs()

        logging.debug("openvpn command: %s", " ".join(ret))
        return ret

    def connect(self):
        kwargs = {}

        if self.debug is False:
            kwargs = {
                'stdout': open(os.devnull, 'w'),
                'stderr': subprocess.STDOUT,
            }

        self.process = TimeoutPopen(self.command(), **kwargs)

        return self.wait_for_openvpn_to_connect()

    def terminate_openvpn(self):
        logging.info("terminating openvpn")

        if not hasattr(self, "process"):
            logging.info("openvpn already dead")
            return

        self.process.terminate()
        rc = self.process.wait(timeout=self.vpn_termination_timeout)

        logging.info('terminating openvpn got rc: %s', rc)
        if rc is None:
            logging.info('timeout after %d seconds while terminating openvpn', self.vpn_termination_timeout)
            self.process.kill()
            rc = self.process.wait(timeout=self.vpn_termination_timeout)
            logging.info('terminating openvpn got rc: %s', rc)

            if rc is None:
                logging.info('timeout after %d seconds while killing openvpn', self.vpn_termination_timeout)
                raise RuntimeError('could not kill openvpn')

    def isConnected(self):
        with OpenVPNManagmentContext("localhost", self.management_port, timeout=1.0) as client:
            self._vpn_ip = client.get_peer_ip()
            return self._vpn_ip is not None

    def openvpn_exited(self):
        return hasattr(self, "process") and self.process.poll() == 0

    def wait_for_openvpn_to_connect(self, retries=15, wait_between_retries=3):
        for attempt in xrange(retries):
            logging.debug("waiting for openvpn to connect (attempt: %d/%d)", attempt+1, retries)
            time.sleep(wait_between_retries)

            if self.openvpn_exited():
                return False

            try:
                if self.isConnected():
                    return True
            except Exception:
                logging.exception("isConnected")

        return False

    def get_peer_address(self):
        return self._vpn_ip


class VPN(TeleportationProvider):
    __provider_name__ = "vpn"

    def __init__(self, params, *args, **kwargs):
        super(VPN, self).__init__(*args, **kwargs)
        self.params = params

    def create_open_vpn_instance(self, host):
        return OpenVPN(
            host=host,
            **self.params
        )

    def teleport(self, place):
        hosts = self.countries[place]

        if isinstance(hosts, basestring):
            hosts = [hosts]

        random.shuffle(hosts)

        _errors = []

        for host in hosts:
            self.vpn = self.create_open_vpn_instance(host)

            try:
                if not self.vpn.connect():
                    raise RuntimeError('error connecting to vpn')

                location = self.where_we_teleported()

                if location != place:
                    raise RuntimeError('teleported to %s while wanting to teleport to %s', location, place)

                return True

            except Exception as e:
                logging.exception('failed teleporting via host %s', host)
                _errors.append(e)
                self.go_home()

        raise RuntimeError('Failed to connect to any vpn host (errors: %s)', _errors)

    def go_home(self):
        if not hasattr(self, 'vpn'):
            raise RuntimeError('not connected')

        self.vpn.terminate_openvpn()
        del self.vpn

    def get_peer_address(self):
        return self.vpn.get_peer_address()
