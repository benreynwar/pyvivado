import unittest
import testfixtures
import logging

from pyvivado import project, config

logger = logging.getLogger(__name__)

default_clock_period = 10
default_extra_clock_periods = 20

class TestCase(unittest.TestCase):
    
    def simulate(self, *args, **kwargs):
        return simulate(*args, **kwargs)

    def check_output(self, *args, **kwargs):
        return check_output(*args, **kwargs)
    

def check_output(output_data, expected_data):
    assert(len(output_data) >= len(expected_data))
    output_data = output_data[:len(expected_data)]
    testfixtures.compare(output_data, expected_data)


def simulate(interface, directory, data, board=config.default_board,
             part=config.default_part, sim_type='hdl',
             clock_period=default_clock_period,
             extra_clock_periods=default_extra_clock_periods):
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
    assert(len(errors) == 0)

    # Run the simulation.
    runtime = '{} ns'.format((len(data) + extra_clock_periods) * clock_period)
    errors, output_data = p.run_simulation(
        input_data=data, runtime=runtime, sim_type=sim_type,
    )
    for error in errors:
        logger.error(error)
    assert(len(errors) == 0)

    return output_data[1:]


def run_test(test_class, test_name='default_test', logging_level=logging.DEBUG):
    config.setup_logging(logging_level)
    suite = unittest.TestSuite()
    suite.addTest(test_class(test_name))
    runner = unittest.TextTestRunner()
    runner.run(suite)

    
