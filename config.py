import os
import logging
import asyncio

from pyvivado import sqlite_collection

basedir = os.path.abspath(os.path.dirname(__file__))
tcldir = os.path.join(basedir, 'tcl')
hdldir = os.path.join(basedir, 'hdl')
testdir = os.path.join(basedir, 'test_outputs')

default_tasks_collection = sqlite_collection.SQLLiteCollection(':memory:')

vivado = r'/opt/Xilinx/Vivado/2014.4/bin/vivado'

default_part = 'xc7k70tfbg676-1'
default_board = ''

hwcodes = [
]
# Real hardware codes look something like '210203826421A'

def get_event_loop():
    loop = asyncio.get_event_loop()
    def wakeup():
        # Hack to get round not catching signals in windows.
        loop.call_later(0.1, wakeup)
    loop.call_later(0.1, wakeup)
    return loop

def setup_for_test():
    setup_logging(logging.DEBUG)

def setup_logging(level):
    "Utility function for setting up logging."
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    # Which packages do we want to log from.
    packages = ('__main__', 'pyvivado',)
    for package in packages:
        logger = logging.getLogger(package)
        logger.addHandler(ch)
        logger.setLevel(level)
    # Warning only packages
    packages = []
    for package in packages:
        logger = logging.getLogger(package)
        logger.addHandler(ch)
        logger.setLevel(logging.WARNING)
    logger.info('Setup logging at level {}.'.format(level))
