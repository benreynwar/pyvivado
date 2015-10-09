'''
Communication with Vivado processes monitoring FPGAs over redis.
Using redis was an awful idea.  It should be done over sockets.
'''

import redis
import datetime
import logging

from pyvivado import config

logger = logging.getLogger(__name__)

r = redis.StrictRedis(host='localhost', port=6379, db=0)


def get_hardware_usage():
    usage = {}
    for board_type in config.hwcodes:
        for hwcode in config.hwcodes[board_type]:
            projdir = hwcode_projdir(hwcode)
            activeA = hwcode_A_active(hwcode)
            activeB = hwcode_B_active(hwcode)
            usage[hwcode] = {
                'projdir': projdir,
                'active': activeA and activeB,
                'monitored': activeA,
            }
    return usage

def summary():
    for board_type in config.hwcodes:
        for hwcode in config.hwcodes[board_type]:
            projdir = hwcode_projdir(hwcode)
            last_A = hwcode_last_A(hwcode)
            last_B = hwcode_last_B(hwcode)
            print('{} {} {} {}'.format(hwcode, last_A, last_B, projdir))

def hwcode_projdir(hwcode):
    projdir = r.get('{}_projdir'.format(hwcode))
    if projdir:
        projdir = projdir.decode('ascii')
    return projdir

def hwcode_last_A(hwcode):
    last_A = r.get('{}_last_A'.format(hwcode))
    if last_A:
        last_A = last_A.decode('ascii')
        as_time = datetime.datetime.strptime(last_A, '%Y%m%d%H%M%S')
    else:
        as_time = None
    return as_time

def hwcode_last_B(hwcode):
    last_B = r.get('{}_last_B'.format(hwcode))
    if last_B:
        last_B = last_B.decode('ascii')
        as_time = datetime.datetime.strptime(last_B, '%Y%m%d%H%M%S')
    else:
        as_time = None
    return as_time

cutoff_time = datetime.timedelta(seconds=10)

def hwcode_A_active(hwcode):
    last_A = hwcode_last_A(hwcode)
    if last_A:
        difference = datetime.datetime.now() - last_A
        active = (difference < cutoff_time)
    else:
        active = False
    return active

def hwcode_B_active(hwcode):
    last_B = hwcode_last_B(hwcode)
    if last_B:
        difference = datetime.datetime.now() - last_B
        active = (difference < cutoff_time)
    else:
        active = False
    return active

def get_free_hwcode(board_type):
    free = None
    for hwcode in config.hwcodes[board_type]:
        if (not hwcode_A_active(hwcode)) and (not hwcode_B_active(hwcode)):
            free = hwcode
    return free

def get_unmonitored_projdir_hwcode(projdir):
    projdir_hwcode = None
    for board_type in config.hwcodes:
        for hwcode in config.hwcodes[board_type]:
            if hwcode_projdir(hwcode) == projdir:
                if (not hwcode_A_active(hwcode)):
                    projdir_hwcode = hwcode
    return projdir_hwcode    

def get_projdir_hwcode(projdir):
    projdir_hwcode = None
    for board_type in config.hwcodes:
        for hwcode in config.hwcodes[board_type]:
            if hwcode_projdir(hwcode) == projdir:
                if hwcode_A_active(hwcode) and (not hwcode_B_active(hwcode)):
                    projdir_hwcode = hwcode
    return projdir_hwcode

