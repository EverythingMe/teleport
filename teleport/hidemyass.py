from vpn import VPN
from concurrency_limiter import ConcurrencyLimiter
import logging

__author__ = 'quatrix'


class HideMyAss(VPN):
    __provider_name__ = "hidemyass"

    def __init__(self, params, *args, **kwargs):
        bucket_name = params.pop('bucket_name')
        concurrency = params.pop('concurrency')
        
        logging.info('initializing provider hidemyass, bucket_name: %s concurrency: %s', bucket_name, concurrency)
        self.concurrency_limiter = ConcurrencyLimiter(name=bucket_name, limit=concurrency)
        super(HideMyAss, self).__init__(params, *args, **kwargs)

    def teleport(self, place):
        self.concurrency_limiter.acquire(blocking=True)
        return super(HideMyAss, self).teleport(place)

    def go_home(self):
        super(HideMyAss, self).go_home()
        self.concurrency_limiter.release()
