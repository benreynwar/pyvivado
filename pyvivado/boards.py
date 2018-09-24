import os

from pyvivado import config

params = {
    'dummy': {
        'clock_frequency': 100,
        'jtagtoaxi_frequency': 100,
        'clock_type': 'Differential_clock_capable_pin',
        'xdc_filename': os.path.join(config.basedir, 'xdc', 'VC709.xdc'),
        'part': 'xc7k70tfbg676-1',
        'xilinx_name': None,
        'name': 'dummy',
    },
    'xilinx:vc709': {
        'clock_frequency': 200,
        'jtagtoaxi_frequency': 100,
        'clock_type': 'Differential_clock_capable_pin',
        'xdc_filename': os.path.join(config.basedir, 'xdc', 'VC709.xdc'),
        'part': 'xc7vx690tffg1761-2',
        'xilinx_name': 'xilinx.com:vc709:part0:1.0',
        'name': 'xilinx:vc709',
    },
    'profpga:uno2000': {
        'clock_frequency': 100,
        'jtagtoaxi_frequency': 100,
        'clock_type': 'Differential_clock_capable_pin',
        'xdc_filename': os.path.join(config.basedir, 'xdc', 'uno2000.xdc'),
        'part': 'xc7v2000T',
        'xilinx_name': None,
        'name': 'profpga:uno2000',
    },        
}

def get_board_params(board):
    if board in params:
        board_params = params[board]
    else:
        raise Exception('Unknown board {}: Trying adding parameters to boards.py'.format(
            board))
    return board_params

