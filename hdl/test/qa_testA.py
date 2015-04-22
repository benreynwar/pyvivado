import unittest
import os
import shutil
import logging
import random

import testfixtures

from pyvivado import config, project
from pyvivado.hdl.test import testA

logger = logging.getLogger(__name__)

class TestTestA(unittest.TestCase):

    def test_one(self):
        directory = os.path.abspath('proj_test_testA')
        data_width = 4
        array_length = 6
        params = {
            'data_width': data_width,
            'array_length': array_length,
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

        # Create project
        interface = testA.get_testA_interface(params)
        p = project.FileTestBenchProject.create_or_update(
            interface=interface,
            directory=directory,
            board=config.default_board,
            part=config.default_part,
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
