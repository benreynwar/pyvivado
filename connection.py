'''
Responsible for communicating with the Vivado processes that
are monitoring the FPGAs.

At the moment this is done via Redis, which was an absolutely
horrible idea, but it's working.

It should really happen over sockets since that would be easy
to do in both python and TCL and wouldn't cause 1 second delay
each time we send a command!

The general vocabulary I'm using is:

An FPGA is monitored if a vivado process is communicating with it.
An FPGA is used if their is also a python script communicating with
that vivado process.
'''
from pyvivado import redis_connection, redis_utils

Connection = redis_connection.Connection

# Find unused monitored hardware running a specific project.
get_projdir_hwcode = redis_utils.get_projdir_hwcode

# Find unused unmonitored hardware.
get_free_hwcode = redis_utils.get_free_hwcode

# Returns information of what the hardware is running and whether
# it is used or monitored.
get_hardware_usage = redis_utils.get_hardware_usage

def kill_free_monitors(directory):
    '''
    Kill any monitors processes that are not being used.
    '''
    hwcode = True
    while hwcode:
        hwcode = get_projdir_hwcode(directory)
        if hwcode:
            conn = Connection(hwcode)
            conn.kill_monitor()
