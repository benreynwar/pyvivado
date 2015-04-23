import os
import time
import redis
import random
import math
import datetime
import logging

logger = logging.getLogger(__name__)

r = redis.StrictRedis(host='localhost', port=6379, db=0)

class Connection(object):

    def __init__(self, hwcode):
        if hwcode is None:
            raise ValueError('Hardware code is None')
        self.name = '{}_comm'.format(hwcode)
        self.listened = '{}_last_B'.format(hwcode)
        self.kill = '{}_kill'.format(hwcode)

    def kill_monitor(self):
        r.set(self.kill, 1)        
        
    def wait_for_response(self, timeout=None):
        waittime = 0.1
        got_response = False
        waiting_time = 0
        while (not got_response) and ((timeout is None) or (waiting_time < timeout)):
            response = r.get(self.name)
            if response[0] == ord('R'):
                got_response=True
            r.set(self.listened, datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
            time.sleep(waittime)
            waiting_time += waittime
        return response

    def write(self, address, data, timeout=None):
        r.set(self.name, 'C W {} {} {}'.format(
            int(address), len(data), ' '.join([str(int(d)) for d in data])))
        self.wait_for_response(timeout=timeout)

    def write_repeat(self, address, data, timeout=None):
        r.set(self.name, 'C WW {} {} {}'.format(
            int(address), len(data), ' '.join([str(int(d)) for d in data])))
        self.wait_for_response(timeout=timeout)

    def read(self, address, length, timeout=None):
        r.set(self.name, 'C R {} {}'.format(int(address), int(length)))
        response = self.wait_for_response(timeout=timeout)
        bits = [int(b.decode('ascii'), 16) for b in response.split()[3:]]
        return bits
        
