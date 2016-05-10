import os
import logging
import random

import testfixtures
import pytest

from pyvivado import config, test_info, test_utils
from pyvivado.hdl.test import testC

logger = logging.getLogger(__name__)


class TestTestC(test_utils.TestCase):

    def default_test(self):
        test_testC(
            width=4,
            sim_type='vivado_hdl',
            pause=False,
        )

combinations = []
for width in (1, 2, 7):
    for sim_type in test_info.test_sim_types:
        combinations.append((width, sim_type))

@pytest.mark.parametrize('width, sim_type', combinations)
def test_testC(width, sim_type, pause=False):
    test_name = 'test_testC'
    directory = os.path.join('test', 'proj_testC_{}'.format(width))
    params = {
        'width': width,
    }

    wait_data = []
    wait_lines = 20
    for wait_index in range(wait_lines):
        wait_data.append({
            'io_i_valid': 0,
            'io_i_data': 0,
            })

    # Make input and expected data
    n_data = 20
    input_data = []
    expected_data = []
    max_data = pow(2, width)-1
    for data_index in range(n_data):
        input_d = {
            'io_i_valid': random.randint(0, 1),
            'io_i_data': random.randint(0, max_data),
        }
        expected_d = {
            'io_o_valid': input_d['io_i_valid'],
            'io_o_data': input_d['io_i_data'],
        }
        input_data.append(input_d)
        expected_data.append(expected_d)

    # Create project
    interface = testC.get_testC_interface(params)
    output_data = test_utils.simulate(
        test_name=test_name,
        interface=interface, directory=directory,
        data=wait_data+input_data,
        sim_type=sim_type,
    )[wait_lines:]
    if pause:
        import pdb
        pdb.set_trace()
    assert(len(output_data) >= len(expected_data))
    output_data = output_data[:len(expected_data)]
    testfixtures.compare(output_data, expected_data)


if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_utils.run_test(TestTestC)
