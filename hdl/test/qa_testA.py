import os
import logging
import random

import testfixtures
import pytest

from pyvivado import config, test_utils, test_info
from pyvivado.hdl.test import testA

logger = logging.getLogger(__name__)


class TestTestA(test_utils.TestCase):

    def default_test(self):
        test_testA(
            data_width=4,
            array_length=6,
            sim_type='hdl',
            external_test=False,
            pause=False,
        )

combinations = []
for data_width in (1, 2, 7):
    for array_length in (1, 5, 19):
        for sim_type in test_info.test_sim_types:
            combinations.append((data_width, array_length, sim_type))

@pytest.mark.parametrize('data_width, array_length, sim_type', combinations)
def test_testA(data_width, array_length, sim_type, pause=False,
               external_test=False):
    directory = os.path.join(config.testdir, 'test', 'proj_testA_{}_{}'.format(
          data_width, array_length))
    params = {
        'data_width': data_width,
        'array_length': array_length,
    }
    test_name = 'test_testA'

    wait_lines = 20
    wait_data = []
    for wait_index in range(wait_lines):
        wait_data.append(
            {'i_valid': 0, 'i_data': 0, 'i_array': [0] * array_length})
    # Make input and expected data
    n_data = 20
    input_data = []
    expected_data = []
    max_data = pow(2, data_width)-1
    for data_index in range(n_data):
        input_d = {
            'i_valid': random.randint(0, 1),
            'i_data': random.randint(0, max_data),
            'i_array': [random.randint(0, max_data)
                        for i in range(array_length)],
        }
        expected_d = {
            'o_valid': input_d['i_valid'],
            'o_data': input_d['i_data'],
            'o_array': input_d['i_array'],
        }
        input_data.append(input_d)
        expected_data.append(expected_d)

    interface = testA.get_testA_interface(params)
    # Create project
    output_data = test_utils.simulate(
        external_test=external_test,
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
    test_utils.run_test(TestTestA)
