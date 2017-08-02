import os
import unittest
import logging
import shutil
import time
import testfixtures

from pyvivado import filetestbench_project, fpga_project, axi
from pyvivado.synopsys import synopsys_project
from pyvivado import vivado_project, test_info
from pyvivado import config
from pyvivado import base_test_utils

logger = logging.getLogger(__name__)

# Import to make available is register
from pyvivado.hdl.wrapper import file_testbench

default_clock_period = 10
default_extra_clock_periods = 20


def compare_p(a, b, pause):
    if (a != b) and pause:
        import pdb
        pdb.set_trace()
    else:
        testfixtures.compare(a, b)


def assert_p(a, pause):
    if (not a) and pause:
        import pdb
        pdb.set_trace()
    else:
        assert(a)
        

class TestCase(unittest.TestCase):

    def simulate(self, *args, **kwargs):
        return simulate(*args, **kwargs)

    def check_output(self, *args, **kwargs):
        return base_test_utils.check_output(*args, **kwargs)


def simulate(directory, data, sim_type,
             test_name='test',
             interface=None,
             params=None,
             board=config.default_board,
             clock_period=default_clock_period,
             extra_clock_periods=default_extra_clock_periods,
             force_refresh=False,
             overwrite_ok=False,
             project_class=filetestbench_project.FileTestBenchProject,
             ):

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
    logger.debug('Making a FileTestBench Project')
    p = project_class(
        params=params, directory=directory,
        overwrite_ok=overwrite_ok,
    )
    logger.debug('Updating input data')
    p.update_input_data(input_data=data, test_name=test_name)
    if sim_type.startswith('vivado'):
        vivado_sim_type = sim_type[len('vivado_'):]
        logger.debug('Making a Vivado Project')
        v = vivado_project.VivadoProject(
            p, overwrite_ok=overwrite_ok, wait_for_creation=True)

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
        v = synopsys_project.SynopsysProject(p)
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


def deploy(directory, params,
           board=config.default_board,
           part=None,
           force_refresh=False,
           overwrite_ok=False,
           ):
    if force_refresh and os.path.exists(directory):
        shutil.rmtree(directory)
    # Make the project.
    p = fpga_project.FPGAProject(
        parameters=params,
        directory=directory,
        board=board,
        overwrite_ok=overwrite_ok,
    )
    v = vivado_project.VivadoProject(
        project=p, board=board, wait_for_creation=True, overwrite_ok=overwrite_ok)
    t_implement = v.implement()
    t_implement.wait()
    t_monitor, conn = v.send_to_fpga_and_monitor()
    return conn


def run_test(test_class, test_name='default_test',
             logging_level=logging.DEBUG):
    suite = unittest.TestSuite()
    suite.addTest(test_class(test_name))
    runner = unittest.TextTestRunner()
    runner.run(suite)


def deploy_and_test(
        params, directory, tests, board=config.default_board,
        part=None, force_refresh=False, overwrite_ok=False):
    '''
    Deploy design to an FPGA and run tests on it there.
    The DUT must have an AXI4-LITE interface.
    '''
    # Make sure this directory is not already deployed.
    v_dir = os.path.join(directory, 'vivado')
    # Import connection down here so that if it's not available
    # we can use other test_utils.
    from pyvivado import connection
    hwcode = connection.get_projdir_hwcode(v_dir)
    assert(hwcode is None)
    conn = deploy(
        directory=directory, params=params,
        board=board,
        part=part,
        force_refresh=force_refresh,
        overwrite_ok=overwrite_ok,
        )
    handler = axi.ConnCommandHandler(conn)
    for test in tests:
        test.set_handler(handler)
        test.prepare()
        test.check()
    # Sleep for 10 seconds so that we can kill monitor
    time.sleep(10)
    # Destroy monitoring process
    connection.kill_free_monitors(v_dir)


def simulate_and_test(
        directory, reset_input, tests,
        test_name='test',
        interface=None,
        params=None,
        wait_lines=20,
        board=config.default_board,
        sim_type=test_info.default_sim_type,
        clock_period=default_clock_period,
        extra_clock_periods=default_extra_clock_periods,
        split_tag=base_test_utils.DEFAULT_SPLIT_TAG,
        pause=False,
        force_refresh=False,
        overwrite_ok=False,
        project_class=filetestbench_project.FileTestBenchProject,
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
    logger.debug('Making input data')
    input_data = base_test_utils.tests_to_input_data(
        reset_input=reset_input, wait_lines=wait_lines, tests=tests)
    logger.debug('Start simulate: simtype is {}'.format(sim_type))
    output_data = simulate(
        interface=None,
        params=params,
        directory=directory,
        data=input_data,
        sim_type=sim_type,
        test_name=test_name,
        overwrite_ok=overwrite_ok,
        project_class=project_class,
    )
    logger.debug('finish simulate')
    base_test_utils.validate_output_data_with_tests(
        input_data=input_data,
        output_data=output_data,
        wait_lines=wait_lines,
        pause=pause,
        tests=tests,
    )


class AxiTest():

    def __init__(self):
        self.handler = None

    def set_handler(self, handler):
        assert(self.handler is None)
        self.handler = handler

    def get_handler(self):
        if self.handler is None:
            raise Exception('Handler on AxiTest not set')
        return self.handler

    def prepare(self):
        raise Exception('Unimplemented')

    def check(self, pause=False):
        raise Exception('Unimplemented')

    def make_input_data(self):
        handler = self.get_handler()
        self.prepare()
        input_data = [
            {'reset': 0,
             'i': d,
            } for d in handler.make_command_dicts()]
        assert(len(input_data) > 0)
        return input_data

    def check_output_data(self, input_data, output_data, pause=False):
        handler = self.get_handler()
        response_dicts = [d['o'] for d in output_data]
        handler.consume_response_dicts(response_dicts)
        self.check(pause=pause)


def axi_run_and_test(
        directory,
        tests,
        test_name='test',
        params=None,
        wait_lines=20,
        board=config.default_board,
        sim_type=test_info.default_sim_type,
        clock_period=default_clock_period,
        extra_clock_periods=default_extra_clock_periods,
        pause=False,
        force_refresh=False,
        overwrite_ok=False,
        ):
    if sim_type == 'fpga':
        deploy_and_test(
            params=params,
            directory=directory,
            tests=tests,
            board=board,
            force_refresh=force_refresh,
            overwrite_ok=overwrite_ok,
            )
    else:
        handler = axi.DictCommandHandler()
        for test in tests:
            logger.debug('setting handler to {}'.format(handler))
            test.set_handler(handler)
        simulate_and_test(
            directory=directory,
            reset_input={'reset': 1, 'd': axi.make_empty_axi4lite_m2s_dict()},
            tests=tests,
            params=params,
            wait_lines=wait_lines,
            sim_type=sim_type,
            clock_period=clock_period,
            extra_clock_periods=extra_clock_periods,
            pause=pause,
            force_refresh=force_refresh,
            overwrite_ok=overwrite_ok,
        )
