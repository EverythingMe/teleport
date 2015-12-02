import json
import logging
import threading
import consul
import os

from time import sleep, time
from contextlib import contextmanager

__author__ = 'quatrix'

@contextmanager
def ConcurrencyLimiterContext(name, limit, ttl=30, blocking=True, timeout=None):
    c = ConcurrencyLimiter(name, limit, ttl)

    try:
        c.acquire(blocking, timeout)
        yield
    finally:
        c.release()


class SemaphoreNodes(object):
    def __init__(self, nodes, limit, lock_key, session_id):
        self.nodes = nodes
        self._limit = limit
        self.lock_key = lock_key
        self.session_id = session_id

    @property
    def contender_keys(self):
        return set([v['Session'] for v in self.nodes if v['Key'] != self.lock_key])

    @property
    def lock_node(self):
        try:
            return [v for v in self.nodes if v['Key'] == self.lock_key][0]
        except (TypeError, IndexError):
            return None

    @property
    def semaphore(self):
        if self.lock_node is None:
            return None

        semaphore = json.loads(self.lock_node['Value'])
        semaphore['Holders'] = [holder for holder in semaphore['Holders'] if holder in self.contender_keys]
        return semaphore

    def get_modify_index(self):
        if self.lock_node is None:
            return 0

        return self.lock_node['ModifyIndex']

    @property
    def holders(self):
        if self.semaphore is None:
            return []

        return self.semaphore['Holders']

    @property
    def limit(self):
        if self.semaphore is None:
            return self._limit

        return self.semaphore['Limit']

    def create_new_lock_node(self):
        return {
            'Limit': self.limit,
            'Holders': self.holders + [self.session_id]
        }

    def can_get_lock(self):
        return len(self.holders) < self.limit

class ConcurrencyLimiter(object):
    def __init__(self, name, limit, ttl=30):
        self.name = name
        self.limit = limit
        self.ttl = ttl

        consul_host = os.environ.get('CONSUL_HOST', '127.0.0.1')
        consul_port = int(os.environ.get('CONSUL_PORT', '8500'))

        logging.info('using consul host: %s port: %d', consul_host, consul_port)
        self.consul = consul.Consul(host=consul_host, port=consul_port)
        self.prefix_key = 'service/{name}/lock/'.format(name=self.name)
        self.lock_key = '{prefix}.lock'.format(prefix=self.prefix_key)

    def get_session_id(self):
        if not hasattr(self, '_session'):
            self._session = self.consul.session.create(name=self.name, ttl=self.ttl, behavior='delete')
        return self._session

    def create_contender_key(self):
        return self.consul.kv.put(
            '{prefix}{session}'.format(
                prefix=self.prefix_key,
                session=self.get_session_id()
            ),
            self.name,
            acquire=self.get_session_id()
        )

    def get_semaphore_nodes(self):
        return SemaphoreNodes(
            nodes=self.consul.kv.get(self.prefix_key, recurse=True)[1],
            limit=self.limit,
            lock_key=self.lock_key,
            session_id=self.get_session_id(),
        )

    def create_lock_node(self, lock_node, modify_index):
        return self.consul.kv.put(
            key=self.lock_key,
            value=json.dumps(lock_node),
            cas=modify_index,
        )

    def get_lock(self):
        semaphore_nodes = self.get_semaphore_nodes()

        if not semaphore_nodes.can_get_lock():
            return False

        return self.create_lock_node(
            lock_node=semaphore_nodes.create_new_lock_node(),
            modify_index=semaphore_nodes.get_modify_index(),
        )

    def keep_alive(self):
        last_renew_time = time()

        while not self._stop_keep_alive.wait(timeout=0.1):
            if time() - last_renew_time > (self.ttl - 5):
                self.consul.session.renew(self.get_session_id())
                last_renew_time = time()

    def start_keep_alive(self):
        self.keep_alive_thread = threading.Thread(target=self.keep_alive)
        self.keep_alive_thread.daemon = True
        self._stop_keep_alive = threading.Event()
        self.keep_alive_thread.start()

    def stop_keep_alive(self):
        logging.info('setting stop keep alive')
        self._stop_keep_alive.set()
        self.keep_alive_thread.join()

    def acquire(self, blocking=True, timeout=None):
        logging.info('trying to get lock for %s (limit=%d)', self.name, self.limit)

        if not self.create_contender_key():
            raise RuntimeError('can\'t create contender_key')

        if blocking:
            self.start_keep_alive()

            t0 = time()

            while not self.get_lock():
                if timeout is not None and time() - t0 > timeout:
                    raise RuntimeError('timeout while trying to get lock')

                logging.info('trying to get lock')
                sleep(1)

        else:
            logging.info('trying to get lock')

            if not self.get_lock():
                raise RuntimeError('can\'t get lock')

            self.start_keep_alive()

        logging.info('got lock')

    def release(self):
        logging.info('releasing lock')
        self.stop_keep_alive()
        self.consul.session.destroy(self.get_session_id())
