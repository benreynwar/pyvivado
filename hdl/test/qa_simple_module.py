import unittest
import os
import logging
import random

import testfixtures

from pyvivado import config, project
from pyvivado.hdl.test import simple_module

logger = logging.getLogger(__name__)

class TestSimpleModule(unittest.TestCase):

    def test_pass_through(self):
        '''
        Tests that the inputs are passing straight through SimpleModule
        as expected.
        '''

        directory = os.path.abspath('proj_testsimplemodule')
        data_width = 4
        params = {
            'data_width': data_width,
        }

        # Make input and expected data
        n_data = 20
        input_data = []
        expected_data = []
        max_data = pow(2, data_width)-1
        for data_index in range(n_data):
            input_d = {
                'i_valid': random.randint(0, 1),
                'i_data': random.randint(0, max_data),
            }
            expected_d = {
                'o_valid': input_d['i_valid'],
                'o_data': input_d['i_data'],
            }
            input_data.append(input_d)
            expected_data.append(expected_d)

        # Create project
        interface = simple_module.get_simple_module_interface(params)
        p = project.FileTestBenchProject.create_or_update(
            interface=interface,
            directory=directory,
        )

        # Run the simulation
        errors, output_data = p.run_simulation(input_data)
        self.assertEqual(len(errors), 0)
        self.check_output(output_data[1:], expected_data)

    def check_output(self, output_data, expected_data):
        self.assertTrue(len(output_data) >= len(expected_data))
        output_data = output_data[:len(expected_data)]
        testfixtures.compare(output_data, expected_data)
        
        
if __name__ == '__main__':
    config.setup_logging(logging.WARNING)
    unittest.main()
