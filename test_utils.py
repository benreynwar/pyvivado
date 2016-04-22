import os
import unittest
import testfixtures
import logging
import shutil

from pyvivado import project, config, external, axi

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


def simulate(interface, directory, data,
             board=config.default_board,
             sim_type='hdl',
             clock_period=default_clock_period,
             extra_clock_periods=default_extra_clock_periods,
             external_test=False,
             force_refresh=False):

    if force_refresh and os.path.exists(directory):
        shutil.rmtree(directory)
    if not os.path.exists(directory):
        os.mkdir(directory)

    if not external_test:
        # Make the project.
        p = project.FileTestBenchProject.create_or_update(
            interface=interface, directory=directory,
            board=board,
        )
        t = p.wait_for_most_recent_task()
        errors = t.get_errors_and_warnings()
        for error in errors:
            logger.error(error)
        assert(len(errors) == 0)

        # Run the simulation.
        runtime = '{} ns'.format((len(data) + extra_clock_periods) *
                                 clock_period)
        errors, output_data = p.run_simulation(
            input_data=data, runtime=runtime, sim_type=sim_type,
        )
        for error in errors:
            logger.error(error)
        assert(len(errors) == 0)

        return output_data[1:]
    else:
        external.make_directory(interface, directory, data)
        return []


def run_test(test_class, test_name='default_test', logging_level=logging.DEBUG):
    suite = unittest.TestSuite()
    suite.addTest(test_class(test_name))
    runner = unittest.TextTestRunner()
    runner.run(suite)


def split_data_for_tests(
        input_data, output_data, split_tag='STARTING_NEW_TEST'):
    test_data = []
    this_test_data = None
    for ipt, opt in zip(input_data, output_data):
        if ipt[split_tag]:
            if this_test_data is not None:
                test_data.append(this_test_data)
            this_test_data = [[], []]
        if this_test_data is not None:
            this_test_data[0].append(ipt)
            this_test_data[1].append(opt)
    if this_test_data is not None:
        test_data.append(this_test_data)
    return test_data


def deploy_and_test(
        interface, directory, tests, board=config.default_board,
        part='', force_refresh=False):
    '''
    Deploy design to an FPGA and run tests on it there.
    The DUT must have an AXI4-LITE interface.
    '''
    p = project.FPGAProject.create_or_update(
        the_builder=interface.builder,
        parameters=interface.parameters,
        directory=directory,
        board=board,
        part=part,
        force_refresh=force_refresh,
    )
    p.wait_for_most_recent_task()
    t_implement = p.implement()
    t_implement.wait()
    t_monitor, conn = p.send_to_fpga_and_monitor()
    for test in tests:
        test.send_to_fpga(conn)
        test.check_futures()


def simulate_and_test(
        interface, directory, reset_input, tests,
        wait_lines=20,
        board=config.default_board,
        sim_type='hdl',
        clock_period=default_clock_period,
        extra_clock_periods=default_extra_clock_periods,
        external_test=False,
        pause=False,
        force_refresh=False):
    '''
    Run a single vivado simulation which contains many independent tests
    that are run one after another in a single simulation.
    '''
    wait_data = [reset_input] * wait_lines
    input_data = []
    for test in tests:
        new_data = test.make_input_data()
        input_data += new_data

    output_data = simulate(
        external_test=external_test,
        interface=interface, directory=directory,
        data=wait_data + input_data,
        sim_type=sim_type,
    )[wait_lines:]

    test_data = split_data_for_tests(input_data, output_data)

    if pause:
        import pdb
        pdb.set_trace()

    # Run test checks
    assert(len(test_data) == len(tests))
    start_index = 0
    for test, data in zip(tests, test_data):
        logger.debug('Running test for data start at index {}'.format(
            start_index))
        start_index += len(data[0])
        test.check_output_data(
            input_data=data[0], output_data=data[1])
