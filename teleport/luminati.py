from teleport import TeleportationProvider
import requests


class Luminati(TeleportationProvider):
    __provider_name__ = "luminati"

    URL = "http://client.luminati.io/api/get_super_proxy?raw=1&user={username}&key={password}"
    PORT = 22225

    def __init__(self, username, password, *args, **kwargs):
        super(Luminati, self).__init__(*args, **kwargs)

        self.username = username
        self.password = password

    def get_super_proxy_url(self):
        return self.URL.format(username=self.username, password=self.password)

    @property
    def is_proxy(self):
        return True

    def get_proxy_username(self, country):
        return "{luminati_username}-country-{country_code}".format(
            luminati_username=self.username,
            country_code=country,
        )

    def get_proxy_auth(self, place):
        return "{username}:{password}".format(
            username=self.get_proxy_username(place),
            password=self.password,
        )

    def _get_super_proxy_ip(self):
        res = requests.get(self.get_super_proxy_url())

        if res.status_code != 200:
            raise RuntimeError("Luminati returned: {}: {}".format(
                res.status_code,
                res.text,
            ))
        
        return res.text

    def get_super_proxy_ip(self):
        if not hasattr(self, "_super_proxy_ip"):
            self._super_proxy_ip = self._get_super_proxy_ip()

        return self._super_proxy_ip

    def get_proxy_address(self):
        return "{ip}:{port}".format(ip=self.get_super_proxy_ip(), port=self.PORT)

    def get_proxies(self):
        return {
            "http": "http://{auth}@{address}".format(
                auth=self.get_proxy_auth(self._place),
                address=self.get_proxy_address(),
            )
        }

    def get_peer_address(self):
        return self.get_proxy_address()

    def teleport(self, place):
        self._place = place
        current_location = self.where_we_teleported()

        if current_location != place:
            return False

        return True
