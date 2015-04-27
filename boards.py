import os

from pyvivado import config

params = {
    'xilinx.com:vc709:part0:1.0': {
        'clock_frequency': 200,
        'clock_type': 'Differential_clock_capable_pin',
        'xdc_filename': os.path.join(config.basedir, 'xdc', 'VC709.xdc'),
    },
}

def get_board_params(board):
    if board in params:
        board_params = params[board]
    else:
        raise Exception('Unknown board {}: Trying adding parameters to boards.py'.format(
            board))
    return board_params

