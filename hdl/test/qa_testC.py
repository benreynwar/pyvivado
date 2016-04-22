import unittest
import os
import logging
import random

import testfixtures

from pyvivado import config, project
from pyvivado.hdl.test import testC

logger = logging.getLogger(__name__)


class TestTestC(unittest.TestCase):

    def test_one(self):
        directory = os.path.abspath('proj_test_testC')
        width = 4
        params = {
            'width': width,
        }

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
        p = project.FileTestBenchProject.create_or_update(
            interface=interface,
            directory=directory,
        )
        t = p.wait_for_most_recent_task()
        errors = t.get_errors()
        self.assertEqual(len(errors), 0)

        # Run the simulation
        runtime = '{} ns'.format((len(input_data) + 20) * 10)
        errors, output_data = p.run_simulation(
            input_data=input_data, runtime=runtime)
        self.check_output(output_data[1:], expected_data)
        self.assertEqual(len(errors), 0)

    def check_output(self, output_data, expected_data):
        self.assertTrue(len(output_data) >= len(expected_data))
        output_data = output_data[:len(expected_data)]
        testfixtures.compare(output_data, expected_data)
        
        
if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    unittest.main()
