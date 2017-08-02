'''
Communication with Vivado processes monitoring FPGAs over redis.
Using redis was an awful idea.  It should be done over sockets.
'''

import os
import time
import redis
import random
import math
import datetime
import logging
from collections import namedtuple

logger = logging.getLogger(__name__)

r = redis.StrictRedis(host='localhost', port=6379, db=0)

from pyvivado import redis_utils

Response = namedtuple('Response', ['length', 'resp', 'data'])

class Connection(object):

    def __init__(self, hwcode):
        if hwcode is None:
            raise ValueError('Hardware code is None')
        logger.info('Creating connection with hwcode: {}'.format(hwcode))
        self.name = '{}_comm'.format(hwcode)
        self.listened = '{}_last_B'.format(hwcode)
        self.kill = '{}_kill'.format(hwcode)
        self.hwcode = hwcode

    def is_monitor_alive(self):
        return redis_utils.hwcode_A_active(self.hwcode)

    def kill_monitor(self, time_limit=10):
        r.set(self.kill, 1)
        counter = 0
        while counter < time_limit and self.is_monitor_alive():
            time.sleep(1)
            counter += 1
        if self.is_monitor_alive():
            raise Exception('Failed to kill monitor.')
        
        
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
        split_response = response.split()
        rsp = Response(
                length=len(split_response[3:]),
                data=[int(v.decode('ascii'), 16) for v in split_response[3:]],
                resp=0,
                )
        return rsp

    def write(self, address, data, timeout=None):
        r.set(self.name, 'C W {} {} {}'.format(
            int(address), len(data), ' '.join([str(int(d)) for d in data])))
        response = self.wait_for_response(timeout=timeout)
        return response

    def write_repeat(self, address, data, timeout=None):
        r.set(self.name, 'C WW {} {} {}'.format(
            int(address), len(data), ' '.join([str(int(d)) for d in data])))
        response = self.wait_for_response(timeout=timeout)
        return response

    def read(self, address, length, timeout=None):
        r.set(self.name, 'C R {} {}'.format(int(address), int(length)))
        response = self.wait_for_response(timeout=timeout)
        return response

    def read_repeat(self, address, length, timeout=None):
        r.set(self.name, 'C RR {} {}'.format(int(address), int(length)))
        response = self.wait_for_response(timeout=timeout)
        return response
