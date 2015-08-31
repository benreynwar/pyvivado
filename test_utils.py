import unittest
import testfixtures
import logging

from pyvivado import project, config

logger = logging.getLogger(__name__)

class TestCase(unittest.TestCase):

    def simulate(self, interface, directory, data, board=config.default_board,
                 part=config.default_part, sim_type='hdl',
                 clock_period=10, extra_clock_periods=20):
        # Make the project.
        p = project.FileTestBenchProject.create_or_update(
            interface=interface, directory=directory,
            board=board,
            part=part,
        )
        t = p.wait_for_most_recent_task()
        errors = t.get_errors_and_warnings()
        for error in errors:
            logger.error(error)
        self.assertEqual(len(errors), 0)

        # Run the simulation.
        runtime = '{} ns'.format((len(data) + extra_clock_periods) * clock_period)
        errors, output_data = p.run_simulation(
            input_data=data, runtime=runtime, sim_type=sim_type,
        )
        for error in errors:
            logger.error(error)
        self.assertEqual(len(errors), 0)

        return output_data

    def check_output(self, output_data, expected_data):
        self.assertTrue(len(output_data) >= len(expected_data))
        output_data = output_data[:len(expected_data)]
        testfixtures.compare(output_data, expected_data)
    
