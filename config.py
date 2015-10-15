import os
import logging
import asyncio

from pyvivado import sqlite_collection

basedir = os.path.abspath(os.path.dirname(__file__))
tcldir = os.path.join(basedir, 'tcl')
hdldir = os.path.join(basedir, 'hdl')
testdir = os.path.join(basedir, 'test_outputs')

default_tasks_collection = sqlite_collection.SQLLiteCollection(':memory:')

vivado = r'C:\Xilinx\Vivado\2014.3\bin\vivado.bat'

default_board = 'xilinx:vc709'

# hwcode and hwtargets are examples.
# Make them match your hardware.
hwcodes = {
    'xilinx:vc709': (
        '210203826421A',
    ),
    'profpga:uno2000': (
        '0000137658c701',
    ),
}

hwtargets = {
    '210203826421A': ('*/xilinx_tcf/Digilent/210203826421A', 15e6),
    '0000137658c701': ('*/xilinx_tcf/Xilinx/0000137658c701', 6e6),
}

def setup_logging(level):
    '''
    Utility function for setting up logging.
    '''
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

# Any output messages from Vivado containing one of these strings will be ignored.
# Delete from or add to this as you wish.
default_ignore_strings = (
    # Ignore warnings about invalid parts
    'as part xc7k325tffg900-2 specified in board_part file is either',
    'as part xc7z045ffg900-2 specified in board_part file is either',
    # Ignore Webtalk communication problems
    '[XSIM 43-3294] Signal EXCEPTION_ACCESS_VIOLATION received',
    # Ignore Warnings from Xilinx DDS Compiler
    '"/proj/xhdhdstaff/saikatb/verific_integ/data/vhdl/src/ieee/distributable/numeric_std.vhd" Line 2547. Foreign attribute on subprog "<=" ignored',
    '"/proj/xhdhdstaff/saikatb/verific_integ/data/vhdl/src/ieee/distributable/numeric_std.vhd" Line 2895. Foreign attribute on subprog "=" ignored',
    # Ignore timescale warnings
    "has a timescale but at least one module in design doesn't have timescale.",
    # Ignore warning about skipping compilation
    "[Vivado 12-3258] Skipping simulation compilation as requested. Simulation will be launched with existing compiled results, if any. To change this behavior, please reset the 'SKIP_COMPILATION' property on the simulation fileset 'sim_1'",
    # Ignore warnings from Ettus files.
    "[VRFC 10-1783] select index 1 into en0 is out of bounds", # in mult.v
)
