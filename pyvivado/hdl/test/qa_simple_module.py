import os
import logging
import random

import pytest

from pyvivado import config, test_utils, test_info

# For register
from pyvivado.hdl.test import simple_module

logger = logging.getLogger(__name__)


class SimpleTest():

    def __init__(self, params, n_data=100):
        self.data_width = params['data_width']
        self.n_data = n_data
        self.max_data = pow(2, self.data_width)-1

    def make_input_data(self):
        n_data = 1000
        input_data = [{
          'i_valid': random.randint(0, 1),
          'i_data': random.randint(0, self.max_data),
          } for i in range(n_data)]
        return input_data

    def check_output_data(self, input_data, output_data, pause):
        # This module is really simple and the outputs should just be the
        # same as the inputs.
        input_valids = [d['i_valid'] for d in input_data]
        output_valids = [d['o_valid'] for d in output_data]
        input_data = [d['i_data'] for d in input_data]
        output_data = [d['o_data'] for d in output_data]
        if (input_valids != output_valids) and pause:
            import pdb
            pdb.set_trace()
        assert(input_valids == output_valids)
        if (input_data != output_data) and pause:
            import pdb
            pdb.set_trace()
        assert(input_data == output_data)


@pytest.mark.parametrize('data_width', (1, 2, 7))
@pytest.mark.parametrize('sim_type', test_info.test_sim_types)
def test_simple_module(data_width, sim_type, pause=False):
    '''
    Tests that the inputs are passing straight through SimpleModule
    as expected.
    '''
    directory = os.path.join(config.testdir, 'test',
                             'proj_simplemodule_{}'.format(data_width))
    params = {
        'data_width': data_width,
        'factory_name': 'SimpleModule'
    }
    # Run the simulation and check that the output is correct.
    test_utils.simulate_and_test(
        params=params,
        directory=directory,
        tests=[SimpleTest(params=params, n_data=1000)],
        reset_input={'i_valid': 0, 'i_data': 0},
        sim_type=sim_type,
    )


if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_simple_module(data_width=4, sim_type='vivado_hdl')
