import os
import unittest
import testfixtures
import logging
import shutil

from pyvivado import filetestbench_project, fpga_project, vcs_project
from pyvivado import config

logger = logging.getLogger(__name__)

# Import to make available is register
from pyvivado.hdl.wrapper import file_testbench
logger.debug('loading file testbench')


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


def simulate(directory, data, test_name, sim_type,
             interface=None,
             params=None,
             board=config.default_board,
             clock_period=default_clock_period,
             extra_clock_periods=default_extra_clock_periods,
             force_refresh=False,
             exclude_fn=None,
             additional_files=[]):

    if interface is None:
        if params is None:
            raise ValueError('No params passed.')
    else:
        logger.warning('Deprecated: Pass parameters rather than interface')
        if params:
            raise ValueError('Do not pass interface as well as params. Just pass params.')
        params = interface.parameters
        params['module_name'] = interface.module_name

    if force_refresh and os.path.exists(directory):
        shutil.rmtree(directory)

    # Make the project.
    logger.info('Making a FileTestBench Project')
    p = filetestbench_project.FileTestBenchProject(
        params=params, directory=directory,
        overwrite_ok=True,
        exclude_fn=exclude_fn,
        additional_files=additional_files,
    )
    logger.debug('Updating input data')
    p.update_input_data(input_data=data, test_name=test_name)
    if sim_type.startswith('vivado'):
        vivado_sim_type = sim_type[len('vivado_'):]
        logger.info('Making a Vivado Project')
        v = vivado_project.VivadoProject(p, overwrite_ok=True)
        if v.new:
            logger.info('Waiting for task')
            t = v.tasks_collection.wait_for_most_recent_task()
            logger.info('Logging errors')
            errors = t.get_errors()
            for error in errors:
                logger.error(error)
            assert(len(errors) == 0)

        # Run the simulation.
        runtime = '{} ns'.format((len(data) + extra_clock_periods) *
                                    clock_period)
        errors, output_data = v.run_simulation(
            test_name=test_name, runtime=runtime, sim_type=vivado_sim_type)
        for error in errors:
            logger.error(error)
        assert(len(errors) == 0)
    elif sim_type.startswith('vcs'):
        vcs_sim_type = sim_type[len('vcs_'):]
        logger.debug('create vcs project')
        v = vcs_project.VCSProject(p)
        logger.debug('run simulation')
        errors, output_data = v.run_simulation(
            test_name=test_name, sim_type=vcs_sim_type)
        logger.debug('finished run simulation')
        for error in errors:
            logger.error(error)
        assert(len(errors) == 0)
    else:
        raise ValueError('Unknown sim_type: {}'.format(sim_type))

    return output_data[1:]


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
        part=None, force_refresh=False):
    '''
    Deploy design to an FPGA and run tests on it there.
    The DUT must have an AXI4-LITE interface.
    '''
    if force_refresh and os.path.exists(directory):
        shutil.rmtree(directory)
    if not os.path.exists(directory):
        os.mkdir(directory)
    p = fpga_project.FPGAProject.create_or_update(
        the_builder=interface.builder,
        parameters=interface.parameters,
        directory=directory,
        board=board,
        part=part,
    )
    p.wait_for_most_recent_task()
    t_implement = p.implement()
    t_implement.wait()
    t_monitor, conn = p.send_to_fpga_and_monitor()
    for test in tests:
        test.send_to_fpga(conn)
        test.check_futures()


def simulate_and_test(
        directory, reset_input, tests, test_name,
        interface=None,
        params=None,
        wait_lines=20,
        board=config.default_board,
        sim_type='vivado_hdl',
        clock_period=default_clock_period,
        extra_clock_periods=default_extra_clock_periods,
        split_tag='STARTING_NEW_TEST',
        pause=False,
        force_refresh=False,
        exclude_fn=None,
        additional_files=[],
    ):
    '''
    Run a single vivado simulation which contains many independent tests
    that are run one after another in a single simulation.
    '''
    logger.debug('staring simulate and test')
    if interface is None:
        if params is None:
            raise ValueError('No params passed.')
    else:
        logger.warning('Deprecated: Pass parameters rather than interface')
        if params:
            raise ValueError('Do not pass interface as well as params. Just pass params.')
        params = interface.parameters
        params['module_name'] = interface.module_name
    wait_data = [reset_input] * wait_lines
    input_data = []
    for test in tests:
        new_data = test.make_input_data()
        new_data[0][split_tag] = True
        for d in new_data[1:]:
            d[split_tag] = False
        input_data += new_data

    logger.debug('start simulate')
    output_data = simulate(
        interface=None,
        params=params,
        directory=directory,
        data=wait_data + input_data,
        sim_type=sim_type,
        test_name=test_name,
        exclude_fn=exclude_fn,
        additional_files=additional_files,
    )[wait_lines:]
    logger.debug('finish simulate')

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


def run_and_test(
        interface, directory, reset_input, tests,
        wait_lines=20,
        board=config.default_board,
        sim_type='hdl',
        clock_period=default_clock_period,
        extra_clock_periods=default_extra_clock_periods,
        pause=False,
        force_refresh=False):
    if sim_type == 'fpga':
        deploy_and_test(
            interface=interface,
            directory=directory + '_fpga',
            tests=tests,
            board=board,
            force_refresh=False)
    else:
        simulate_and_test(
            interface=interface,
            directory=directory,
            reset_input=reset_input,
            tests=tests,
            wait_lines=wait_lines,
            board=board,
            sim_type=sim_type,
            clock_period=clock_period,
            extra_clock_periods=extra_clock_periods,
            pause=pause,
            force_refresh=force_refresh,
            )
