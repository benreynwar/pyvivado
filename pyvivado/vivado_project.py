import os
import logging
import shutil
import time

import fusesoc_generators
from axilent import handlers
import slvcodec

from pyvivado import jtagtestbench_generator
from pyvivado import boards, tasks_collection, hash_helper, config
from pyvivado import params_helper, vivado_task, task, base_project

# Want to be able to use when redis not available
try:
    from pyvivado import redis_utils
    from pyvivado import connection
except ImportError:
    redis_utils = 'Failed to import redis_utils and connection'

logger = logging.getLogger(__name__)


def make_clock_constraint(fn, clock_name, frequency):
    clock_period = 1000/frequency
    constraint = 'create_clock -period {} -waveform {{0.000 {} }} [get_ports {}]'.format(
        clock_period, clock_period/2, clock_name)
    with open(fn, 'w') as f:
        f.write(constraint)


class VivadoProject(object):
    '''
    The base class for python wrappers around Vivado Projects.

    Also does some management of Vivado processes (`Task`s) that are run.
    '''

    def get_creation_status(self):
        creation_fn = os.path.join(self.directory, 'creation.txt')
        try:
            with open(creation_fn, 'x') as f:
                f.write('CREATING')
                status = 'DOCREATE'
        except FileExistsError:
            with open(creation_fn, 'r') as f:
                status = f.readline()
        return status

    def __init__(self, project, part=None, board=None, overwrite_ok=False,
                 use_without_refresh=False, wait_for_creation=False, out_of_context=False,
                 frequency=None, frequency_b=None, clock_name=None):
        '''
        Create a new Vivado project.

        Args:
            `project`: A BaseProject that we want to create a vivado project based upon.
            `part`: The 'part' to use when implementing.
            `board`: The 'board' to used when implementing.

        Returns:
            A python `VivadoProject` object that wraps a Vivado project.
            The Vivado project itself will still be in the middle of being
            created when the function returns.
        '''
        logger.debug('Initialize vivado project.')
        self.project = project
        self.directory = self.directory_from_project(project)
        self.out_of_context = out_of_context
        task_0_dir = os.path.join(self.directory, 'task_0')
        self.new = True
        if os.path.exists(task_0_dir):
            task_0 = task.Task(task_0_dir)
            if task_0.is_finished():
                self.new = False

        self.filename = os.path.join(self.directory, 'TheProject.xpr')
        if not self.new:
            if not os.path.exists(self.filename):
                max_waits = 30
                n_waits = 0
                while ((not os.path.exists(self.filename)) and
                       (n_waits < max_waits)):
                    time.sleep(1)
                    n_waits += 1
                if n_waits >= max_waits:
                    raise Exception('Directory exists, but project file does not.')

        params_fn = os.path.join(self.directory, 'params.txt')
        self.params_helper = params_helper.ParamsHelper(params_fn)
        old_params = self.params_helper.read()
        if old_params is not None:
            if part is None:
                part = old_params['part']
            if board is None:
                board = old_params['board']
        new_params = {
            'part': part,
            'board': board,
            }
        refresh = False
        if old_params is not None:
            if not old_params == new_params:
                if not overwrite_ok:
                    raise Exception('Part or Board have changed. {} -> {}'.format(
                        old_params, new_params))
                else:
                    refresh = True
        else:
            if not self.new:
                import pdb
                pdb.set_trace()
                raise Exception('No Part or Board parameters found for existing vivado project.')
        self.part = part
        self.board = board
        self.hash_helper = hash_helper.HashHelper(self.directory, self.project.get_hash)
        if (not self.new) and self.hash_helper.is_changed():
            if not overwrite_ok:
                if not use_without_refresh:
                    raise Exception('Hash has changed in project but overwrite is not allowed.')
            else:
                refresh = True
        if refresh:
            shutil.rmtree(self.directory)
            logger.debug('Deleting old vivado project directory.')
        self.tasks_collection = tasks_collection.TasksCollection(
            self.directory, task_type=vivado_task.VivadoTask)
        if self.new or refresh:
            logger.debug('Making new vivado project directory')
            os.mkdir(self.directory)
            self.params_helper.write(new_params)
            self.hash_helper.write()

            if self.out_of_context and frequency and clock_name:
                fn = os.path.join(self.directory, 'clock_constraint.xdc')
                make_clock_constraint(fn, clock_name, frequency)
                self.additional_constraint_files = [fn]
            else:
                self.additional_constraint_files = []

            logger.debug('launching create task')
            self.create_task = self.launch_create_task()
            if wait_for_creation:
                self.create_task.wait()
        else:
            self.create_task = None

    @classmethod
    def directory_from_project(cls, project):
        return os.path.join(project.directory, 'vivado')

    @staticmethod
    def make_create_vivado_project_command(
            directory, design_files, simulation_files, ips, part, board,
            top_module, out_of_context):
        # Format the IP infomation into a TCL-friendly format.
        tcl_ips = []
        for ip_name, ip_properties, module_name in ips:
            ip_version = ''
            tcl_start = '{ip_name} {{{ip_version}}} {module_name}'.format(
                ip_name=ip_name, ip_version=ip_version,
                module_name=module_name)
            tcl_properties = ' '.join(
                ['{{ {} {} }}'.format(k, v) for k, v in ip_properties.items()])
            tcl_ip = '{} {{ {} }}'.format(tcl_start, tcl_properties)
            tcl_ips.append(tcl_ip)
        tcl_ips = ' '.join(['{{ {} }}'.format(ip) for ip in tcl_ips])
        # Fail if a project already exists in this directory.
        if os.path.exists(os.path.join(directory, 'TheProject.xpr')):
            raise Exception('Vivado Project already exists.')
        # Write a hash that specifies the state of the files when the
        # Vivado project was created.
        if board in boards.params:
            board_params = boards.params[board]
            board_name = board_params['xilinx_name']
            part_name = board_params['part']
            assert part is None
        else:
            board_name = board
            part_name = part
        if board_name is None:
            board_name = ''
        if part_name is None:
            part_name = ''
        if not out_of_context:
            out_of_context = ''
        else:
            out_of_context = 'out_of_context'
        # Generate a TCL command to create the project.
        command_template = '''::pyvivado::create_vivado_project {{{directory}}} {{ {design_files} }}  {{ {simulation_files} }} {{{part}}} {{{board}}} {{{ips}}} {{{top_module}}} {{{out_of_context}}}'''
        command = command_template.format(
            directory=directory,
            design_files=' '.join([
                '{'+f+'}' for f in design_files]),
            simulation_files=' '.join([
                '{'+f+'}' for f in simulation_files]),
            part=part_name,
            board=board_name,
            ips=tcl_ips,
            top_module=top_module,
            out_of_context=out_of_context,
        )
        return command

    @staticmethod
    def make_create_vivado_simset_command(
            directory, test_name, simulation_files):
        # Generate a TCL command to create the simset.
        command_template = '''::pyvivado::create_simset {{{directory}}} {{{test_name}}} {{ {simulation_files} }};'''
        command = command_template.format(
            directory=directory,
            test_name=test_name,
            simulation_files=' '.join([
                '{'+f+'}' for f in simulation_files]),
        )
        return command

    def launch_create_task(self):
        design_files = self.project.files_and_ip['design_files']
        if self.additional_constraint_files:
            design_files += self.additional_constraint_files
        simulation_files = self.project.files_and_ip['simulation_files']
        ips = self.project.files_and_ip['ips']
        top_module = self.project.files_and_ip['top_module']
        command = self.make_create_vivado_project_command(
            self.directory, design_files, simulation_files,
            ips, self.part, self.board, top_module, self.out_of_context)
        logger.debug('Command is {}'.format(command))
        logger.debug('Directory of new project is {}.'.format(self.directory))
        # Create a task to create the project.
        t = vivado_task.VivadoTask.create(
            collection=self.tasks_collection,
            description='Creating a new Vivado project.',
            command_text=command,
        )
        t.run()
        return t

    def utilization_file(self, from_synthesis=False):
        if from_synthesis:
            fn = 'synth_utilization.txt'
        else:
            fn = 'impl_utilization.txt'
        fn = os.path.join(self.directory, fn)
        return fn

    def power_file(self, from_synthesis=False):
        if from_synthesis:
            fn = 'synth_power.txt'
        else:
            fn = 'impl_power.txt'
        fn = os.path.join(self.directory, fn)
        return fn

    def get_power(self, from_synthesis=False, names=None):
        if names is None:
            names = ['Total']
        fn = self.power_file(from_synthesis=from_synthesis)
        pwers = {}
        with open(fn, 'r') as f:
            for line in f:
                bits = [s.strip() for s in line.split('|')]
                if (len(bits) == 7) and (bits[1] in names):
                    pwers[bits[1]] = float(bits[2])
        return pwers

    def get_utilization(self, from_synthesis=False):
        fn = self.utilization_file(from_synthesis=from_synthesis)
        if not os.path.exists(fn):
            t = self.generate_reports(from_synthesis=from_synthesis)
            t.wait()
            t.log_messages(t.get_messages())
        parents = []
        with open(fn, 'r') as f:
            found_hier = False
            for line in f:
                if not found_hier:
                    bits = [s.strip() for s in line.split('|')]
                    if (len(bits) > 1) and (bits[1] == 'Instance'):
                        categories = bits[3: -1]
                        found_hier = True
                else:
                    bits = line.split('|')
                    if len(bits) > 2:
                        hier_level = (len(bits[1]) - len(bits[1].lstrip()) - 1)//2
                        this_ut = {
                            'Instance': bits[1].strip(),
                            'Module': bits[2].strip(),
                            'children': [],
                        }
                        for index, category in enumerate(categories):
                            this_ut[category] = int(bits[index+3].strip())
                        if len(parents) == 0:
                            assert(hier_level == 0)
                            parents = [this_ut]
                        else:
                            parent = parents[hier_level-1]
                            parent['children'].append(this_ut)
                            parents = parents[:hier_level] + [this_ut]
        return parents[0]

    def synthesize(self, keep_hierarchy=False):
        '''
        Spawn a Vivado process to synthesize the project.
        '''
        tcl_keep_hierarchy = '"keep_hierarchy"' if keep_hierarchy else '{{}}'
        tcl_out_of_context = '"out_of_context"' if self.out_of_context else '{{}}'
        command_templ = '::pyvivado::open_and_synthesize {{{}}} ' + tcl_keep_hierarchy + ' ' + tcl_out_of_context
        t = vivado_task.VivadoTask.create(
            command_text=command_templ.format(self.directory),
            description='Synthesize project.',
            collection=self.tasks_collection,
        )
        t.run()
        return t

    def implement(self, keep_hierarchy=False):
        '''
        Spawn a Vivado process to implement the project.
        '''
        tcl_keep_hierarchy = '"keep_hierarchy"' if keep_hierarchy else '{{}}'
        tcl_out_of_context = '"out_of_context"' if self.out_of_context else '{{}}'
        t = vivado_task.VivadoTask.create(
            command_text='::pyvivado::open_and_implement {{{}}} {} {}'.format(
                self.directory, tcl_keep_hierarchy, tcl_out_of_context),
            description='Implement project.',
            collection=self.tasks_collection,
        )
        t.run()
        return t

    def generate_reports(self, from_synthesis=False):
        '''
        Spawn a Vivado process to generate reports
        '''
        if from_synthesis:
            command_templ = '::pyvivado::generate_synth_reports {{{}}}'
        else:
            command_templ = '::pyvivado::generate_impl_reports {{{}}}'
        t = vivado_task.VivadoTask.create(
            command_text=command_templ.format(self.directory),
            description='Generate reports.',
            tasks_collection=self.tasks_collection,
        )
        t.run()
        return t

    def run_simulation(self, test_name, test_bench_name, runtime, sim_type='hdl'):
        '''
        Spawns a vivado process that will run a simulation of the project.

        Args:
            `test_name`: A label for the test.
            `test_bench_name`: The top level test bench name.
            `runtime`: A string specifying the runtime.
            'sim_type`: The string specifying the simulation type.  It can be
               'hdl', 'post_synthesis', or 'timing.

        Returns a (errors, output_data) tuple where:
            `errors`: If a list of errors produced by the simulation task.
            `output_data`: A list of dictionaries of the output wire values.
        '''
        simulation_files = self.project.file_helper.read()['simulation_files']
        command_template = '''
open_project {{{project_filename}}}
::pyvivado::run_{sim_type}_simulation {{{directory}}} {{{test_name}}} {{{test_bench_name}}} {{{runtime}}} {{ {simulation_files} }}
'''
        command = command_template.format(
            project_filename=self.filename, runtime=runtime, sim_type=sim_type,
            test_name=test_name,
            test_bench_name=test_bench_name,
            directory=self.directory.replace('\\', '/'),
            simulation_files=' '.join([
                '{'+f+'}' for f in simulation_files]),
            )
        # Create a task to run the simulation.
        t = vivado_task.VivadoTask.create(
            collection=self.tasks_collection,
            description='Running a HDL simulation.',
            command_text=command,
        )
        # Run the simulation task and wait for it to complete.
        t.run_and_wait()
        errors = t.get_errors()
        return errors

    def get_monitors_hwcode(self, monitor_task):
        '''
        Get the hardware code for the FPGA that this project has been deployed to.
        '''
        max_waits = 120
        n_waits = 0
        hwcode = None
        while (hwcode is None) and (n_waits < max_waits) and (not monitor_task.is_finished()):
            hwcode = connection.get_projdir_hwcode(self.directory)
            n_waits += 1
            time.sleep(1)
        # If the task is finished something must have gone wrong
        # so log it's messages.
        if monitor_task.is_finished():
            monitor_task.log_messages(monitor_task.get_messages())
        deploy_errors = monitor_task.get_errors()
        logger.debug('Waited {}s to see deployment'.format(n_waits))
        if (len(deploy_errors) != 0):
            raise Exception('Got send_to_fpga_and_monitor errors.')
        if hwcode is None:
            raise Exception('Failed to deploy project')
        return hwcode

    def wait_for_monitor(self, hwcode, monitor_task):
        max_waits = 120
        n_waits = 0
        # Check to see that correct proj_dir is associated with the hwcode
        # and that it has been monitored recently.
        def checks_out():
            projdir_correct = (self.directory == connection.get_hwcode_projdir(hwcode))
            active = redis_utils.hwcode_A_active(hwcode)
            return projdir_correct and active
        while (not checks_out()) and (n_waits < max_waits) and (not monitor_task.is_finished()):
            n_waits += 1
            time.sleep(1)
        # If the task is finished something must have gone wrong
        # so log it's messages.
        if monitor_task.is_finished():
            monitor_task.log_messages(monitor_task.get_messages())
        deploy_errors = monitor_task.get_errors()
        logger.debug('Waited {}s to see deployment'.format(n_waits))
        if (len(deploy_errors) != 0):
            raise Exception('Got send_to_fpga_and_monitor errors.')

    def monitor_existing(self):
        '''
        Find an FPGA running this project that is not already monitored, and start
        monitoring it.

        Returns a (t, conn) tuple where:
            `t`: is the `Task` wrapping the Vivado process monitoring the FPGA, and
            `conn`: is the `Connection` with which this python process can
                 communicate the monitor.
        '''
        hwcode = redis_utils.get_unmonitored_projdir_hwcode(self.directory)
        if hwcode is None:
            raise Exception('No free hardware running this project found.')
        hwtarget, jtagfreq = config.hwtargets[hwcode]
        description = 'Monitor Redis connection and pass command to FPGA.'
        t = vivado_task.VivadoTask.create(
            collection=self.tasks_collection,
            command_text='::pyvivado::monitor_redis {} {} {:0} 0'.format(hwcode, hwtarget, int(jtagfreq)),
            description=description,
        )
        t.run()
        self.wait_for_monitor(hwcode=hwcode, monitor_task=t)
        conn = connection.Connection(hwcode)
        return t, conn


    def send_to_fpga_and_monitor(self, fake=False):
        '''
        Send the bitstream of this project to an FPGA and start
        monitoring that FPGA.

        Returns a (t, conn) tuple where:
            `t`: is the `Task` wrapping the Vivado process monitoring the FPGA, and
            `conn`: is the `Connection` with which this python process can
                 communicate the monitor.
        '''
        if fake:
            # First kill any monitors connected to this project.
            connection.kill_free_monitors(self.directory)
            fake_int = 1
            description = 'Faking sending the project to fpga and monitoring.'
        else:
            fake_int = 0
            description = 'Sending project to fpga and monitoring.'
        # Get the hardware code for an unmonitored FPGA.
        self.params = self.params_helper.read()
        hwcode = redis_utils.get_free_hwcode(self.params['board'])
        if hwcode is None:
            raise Exception('No free hardware found.')
        hwtarget, jtagfreq = config.hwtargets[hwcode]
        logger.info('Using hardware: {}'.format(hwcode))
        # Spawn a Vivado process to deploy the bitstream and
        # start monitoring.
        t = vivado_task.VivadoTask.create(
            collection=self.tasks_collection,
            command_text='::pyvivado::send_to_fpga_and_monitor {{{}}} {} {} {} {}'.format(
                self.directory, hwcode, hwtarget, int(jtagfreq), fake_int),
            description=description,
        )
        t.run()
        # Wait for the task to start monitoring and get the
        # hardware code of the free fpga.
        self.wait_for_monitor(hwcode=hwcode, monitor_task=t)
        # Create a Connection object for communication with the FPGA/
        conn = connection.Connection(hwcode)
        return t, conn

    def implement_deploy_and_run_tests(self, tests):
        t_implement = self.implement()
        t_implement.wait()
        t_monitor, conn = self.send_to_fpga_and_monitor()

        handler = handlers.ConnCommandHandler(conn)
        for test in tests:
            test.prepare(handler)
            test.check()
        # Sleep for 10 seconds so that we can kill monitor
        time.sleep(10)
        # Destroy monitoring process
        connection.kill_free_monitors(self.directory)
