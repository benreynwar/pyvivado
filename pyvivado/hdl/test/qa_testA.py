import os
import logging
import random

import testfixtures
import pytest

from pyvivado import config, params_helper
from pyvivado import test_utils, test_info

# Load into register
from pyvivado.hdl.test import testA

logger = logging.getLogger(__name__)


class TestOne():

    def __init__(self, params, n_data=20):
        self.n_data = n_data
        self.data_width = params['data_width']
        self.array_length = params['array_length']
        self.max_data = pow(2, self.data_width)-1

    def make_input_data(self):
        n_data = 20
        max_data = pow(2, self.data_width)-1
        input_data = [
            {
                'i_valid': random.randint(0, 1),
                'i_data': random.randint(0, max_data),
                'i_array': [random.randint(0, max_data)
                            for i in range(self.array_length)],
            } for i in range(n_data)]
        return input_data

    def check_output_data(self, input_data, output_data):
        testfixtures.compare([d['i_valid'] for d in input_data],
                             [d['o_valid'] for d in output_data])
        testfixtures.compare([d['i_data'] for d in input_data],
                             [d['o_data'] for d in output_data])
        testfixtures.compare([d['i_array'] for d in input_data],
                             [d['o_array'] for d in output_data])

@pytest.mark.parametrize('data_width', (1, 2, 7))
@pytest.mark.parametrize('array_length', (1, 5, 19))
@pytest.mark.parametrize('sim_type', test_info.test_sim_types)
def test_testA(data_width, array_length, sim_type, pause=False,
               external_test=False):
    random.seed(0)
    directory = os.path.join(config.testdir, 'test', 'proj_testA_{}_{}'.format(
          data_width, array_length))
    params = params_helper.make_base_params({
        'data_width': data_width,
        'array_length': array_length,
        'factory_name': 'TestA',
    })

    tests = (TestOne(params),)

    reset_input = {
        'i_valid': 0,
        'i_data': 0,
        'i_array': [0 for i in range(array_length)],
        }

    test_utils.simulate_and_test(
        params=params,
        directory=directory,
        tests=tests,
        reset_input=reset_input,
        sim_type=sim_type,
        pause=pause,
    )


if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_testA(
        data_width=2,
        array_length=5,
        sim_type=test_info.default_sim_type,
        pause=False,
    )
