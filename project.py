import os
import fnmatch
import logging
import time
import json
import hashlib
import shutil

from pyvivado import config, task, utils, interface, builder, redis_utils
from pyvivado import connection, sqlite_collection, boards
from pyvivado.hdl.wrapper import inner_wrapper, file_testbench, jtag_axi_wrapper

logger = logging.getLogger(__name__)


class Project(object):
    '''
    The base class for python wrappers around Vivado Projects.

    Also does some management of Vivado processes (`Task`s) that are run.
    '''
    
    @classmethod
    def default_tasks_collection(cls, directory):
        '''
        The location of the database where we keep track of tasks.
        '''
        db_fn = os.path.join(directory, 'tasks.db')
        tasks_collection = sqlite_collection.SQLLiteCollection(db_fn)        
        return tasks_collection

    @staticmethod
    def hash(design_files, simulation_files, ips):
        '''
        Generate a hash that based on the files and IP in the project.
        This is used to tell when the files in the project have been changed.
        '''
        h = hashlib.sha1()
        design_files = sorted(list(design_files))
        simulation_files = sorted(list(simulation_files))
        # Sort IPs by their name.
        def get_name(a):
            return a[2]
        ips = sorted(list(ips), key=get_name)
        # Check that names are unique
        names = [a[2] for a in ips]
        assert(len(names) == len(set(names)))
        design_files_hash = utils.files_hash(design_files)
        simulation_files_hash = utils.files_hash(simulation_files)
        # FIXME: Not sure whether this will work properly for
        # the ips
        ips_hash = str(tuple(ips)).encode('ascii')
        h.update(utils.files_hash(design_files))
        h.update(utils.files_hash(simulation_files))
        h.update(ips_hash)
        logger.debug('design {} simulation {} ips {}'.format(
            design_files_hash, simulation_files_hash, ips_hash))
        return h.digest()

    @staticmethod
    def read_hash(directory):
        '''
        When a project is generated we write a hash so we know what state the
        files were in, and we can tell if the files have changed since the
        project was generated.
        Here we read that hash.
        '''
        hash_fn = os.path.join(directory, 'hash.txt')
        if not os.path.exists(hash_fn):
            h = None
        else:
            with open(hash_fn, 'rb') as f:
                h = f.read()
        return h

    @staticmethod
    def write_hash(directory, h):
        '''
        Write a record of the project's hash.
        '''
        hash_fn = os.path.join(directory, 'hash.txt')
        with open(hash_fn, 'wb') as f:
            f.write(h)

    @classmethod
    def create(cls, directory, design_files, simulation_files,
               tasks_collection=None,
               part='', board='', ips=[],
               top_module=''):
        '''
        Create a new Vivado project.

        Args:
            `directory`: The directory where the project will be created.
            `design_files`: The files for the synthesizable fraction of the design.
            `simulation_files`: The simulation files (i.e. non-synthesizable).
            `tasks_collection`: How to keep track of the Vivado processes we start.
            `part`: The 'part' to use when implementing.
            `board`: The 'board' to used when implementing.
            `ips`: A list of (ip name, ip parameters, module name) tuples that are
                   used to specify the required IP blocks.
            `top_module`: The name of the top level module.

        Returns:
            A python `Project` object that wraps a Vivado project.  The Vivado project
            itself will still be in the middle of being created when the function
            returns.
        '''
        if tasks_collection is None:
            tasks_collection = cls.default_tasks_collection(directory)
        # Format the IP infomation into a TCL-friendly format.
        tcl_ips = []
        for ip_name, ip_properties, module_name in ips:
            ip_version = ''
            tcl_start = '{ip_name} {{{ip_version}}} {module_name}'.format(
                ip_name=ip_name, ip_version=ip_version, module_name=module_name)
            tcl_properties = ' '.join(
                ['{{ {} {} }}'.format(k, v) for k,v in ip_properties])
            tcl_ip = '{} {{ {} }}'.format(tcl_start, tcl_properties)
            tcl_ips.append(tcl_ip)
        tcl_ips = ' '.join(['{{ {} }}'.format(ip) for ip in tcl_ips])
        # Fail if a project already exists in this directory.
        if os.path.exists(os.path.join(directory, 'TheProject.xpr')):
            raise Exception('Project already exists.')
        # Write a hash that depends on the files and IPs.
        # We use this later to check whether any of the files or 
        # IP requirements have changed.
        cls.write_hash(directory, cls.hash(
            design_files=design_files,
            simulation_files=simulation_files,
            ips=ips,
        ))
        # Generate a TCL command to create the project.
        command_template = '''::pyvivado::create_vivado_project {{{directory}}} {{ {design_files} }} {{ {simulation_files} }} {{{part}}} {{{board}}} {{{ips}}} {{{top_module}}}'''
        command = command_template.format(
            directory=directory,
            design_files=' '.join([
                '{'+f+'}' for f in design_files]),
            simulation_files=' '.join([
                '{'+f+'}' for f in simulation_files]),
            part=part,
            board=board,
            ips=tcl_ips,
            top_module=top_module,
        )
        logger.debug('Command is {}'.format(command))
        logger.debug('Directory of new project is {}.'.format(directory))
        # Create a task to create the project.
        t = task.VivadoTask.create(
            parent_directory=directory,
            description='Creating a new Vivado project.',
            command_text=command,
            tasks_collection=tasks_collection
        )
        t.run()
        # Finally create the python project wrapper and return it.
        # Note that the Vivado process is still running and the Vivado
        # project itself is still in the middle of being created.
        p = cls(directory, tasks_collection)
        return p
    
    def __init__(self, directory, tasks_collection=None):
        '''
        Create a python wrapper around a Vivado project.

        Args:
           `directory`: Location of the vivado project.
           `tasks_collection`: How we keep track of the Vivado processes.
        '''
        self.directory = directory
        if tasks_collection is None:
            self.tasks_collection = self.default_tasks_collection(directory)
        else:
            self.tasks_collection = tasks_collection
        self.filename = os.path.join(directory, 'TheProject.xpr')
        
    def get_tasks(self):
        '''
        Get all the tasks (Vivado processes) that have been run on this proejct.
        We get them from their directories in the project directory rather
        than from checking the `tasks_collection`.
        '''
        ids = [int(fn[5:]) for fn in os.listdir(self.directory)
               if fnmatch.fnmatch(fn, 'task_*')]
        tasks = [
            task.VivadoTask(_id=_id, tasks_collection=self.tasks_collection)
            for _id in ids]
        return tasks

    def unfinished_tasks(self):
        '''
        Gets a list of all tasks on this project that have not finished.
        '''
        tasks = [t for t in self.get_tasks() if not t.is_finished()]
        return tasks

    def get_most_recent_task(self):
        '''
        Get the most recent task that was run on this project.
        '''
        ids = [int(fn[5:]) for fn in os.listdir(self.directory)
               if fnmatch.fnmatch(fn, 'task_*')]
        ids.sort()
        t = task.VivadoTask(_id=ids[0], tasks_collection=self.tasks_collection)
        return t

    def wait_for_most_recent_task(self):
        '''
        Get the most recent task that was run on this project and wait
        for it to complete.
        '''
        t = self.get_most_recent_task()
        while not t.is_finished():
            logger.debug('Waiting for tasks to finish.')
            time.sleep(1)
        t.log_messages(t.get_messages())
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

    def get_power(self, from_synthesis=False):
        fn = self.power_file(from_synthesis=from_synthesis)
        pwer = None
        with open(fn, 'r') as f:
            for line in f:
                bits = [s.strip() for s in line.split('|')]
                if (len(bits) == 4) and (bits[1] == 'dut'):
                    pwer = float(bits[2])
        return pwer

    def get_utilization(self, from_synthesis=False):
        fn = self.utilization_file(from_synthesis=from_synthesis)
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
        if keep_hierarchy:
            command_templ='::pyvivado::open_and_synthesize {{{}}} "keep_hierarchy"'
        else:
            command_templ='::pyvivado::open_and_synthesize {{{}}}'
        t = task.VivadoTask.create(
            parent_directory=self.directory,
            command_text=command_templ.format(self.directory),
            description='Synthesize project.',
            tasks_collection=self.tasks_collection,
        )
        t.run()
        return t

    def implement(self):
        '''
        Spawn a Vivado process to implement the project.
        '''
        t = task.VivadoTask.create(
            parent_directory=self.directory,
            command_text='::pyvivado::open_and_implement {{{}}}'.format(
                self.directory),
            description='Implement project.',
            tasks_collection=self.tasks_collection,
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
        t = task.VivadoTask.create(
            parent_directory=self.directory,
            command_text=command_templ.format(self.directory),
            description='Generate reports.',
            tasks_collection=self.tasks_collection,
        )
        t.run()
        return t        


class BuilderProject(Project):
    '''
    A wrapper around a Vivado project.  It assumes that the project was
    created using `Builder`s rather than by explicitly listing the files.
    '''

    @classmethod
    def predict_hash(cls, design_builders, simulation_builders, parameters,
                     temp_directory, directory):
        '''
        Get the project hash for the project that these builders would create.

        Args:
            `design_builders`: The builders responsible for the synthesizable code.
            `simulation_builders`: The builders responsible for the simulation code.
            `parameters`: Top level parameters used to generated the design.
            `temp_directory`: We temporary directory where we'll generate the files
                so we can work out the hash.
            `directory`: The real project location.  This is required since some
                simulation files may need this information.
        '''
        # Make a new directory for temporary files.
        if os.path.exists(temp_directory):
            shutil.rmtree(temp_directory)
        os.makedirs(temp_directory)
        # Build all the required files.
        design_requirements = builder.build_all(
            temp_directory, top_builders=design_builders, top_params=parameters)
        simulation_requirements = builder.build_all(
            temp_directory, top_builders=simulation_builders,
            top_params=parameters, false_directory=directory)
        # Work out what IP blocks are required.
        ips = builder.condense_ips(
            design_requirements['ips'] + simulation_requirements['ips'])
        # And generate the hash.
        new_hash = cls.hash(
            design_files=design_requirements['filenames'],
            simulation_files=simulation_requirements['filenames'],
            ips=ips)
        return new_hash
            

    @classmethod
    def delete_if_changed(cls, design_builders, simulation_builders, parameters, directory,
               tasks_collection=None, part='', board='', top_module=''):
        '''
        Check if the dependencies of the project have changed.  If they have delete
        the project so that it can be recreated later.

        Args:
            `design_builders`: The builders responsible for the synthesizable code.
            `simulation_builders`: The builders responsible for the simulation code.
            `parameters`: Top level parameters used to generated the design.
            `temp_directory`: We temporary directory where we'll generate the files
                so we can work out the hash.
            `directory`: The real project location.  This is required since some
                simulation files may need this information.
            `tasks_collection`: How we keep track of Vivado processes.
            `part`: The 'part' to use when implementing.
            `board`: The 'board' to use when implementing.
            `top_module`: The top level module in the design.
        '''
        if os.path.exists(directory):
            # Check that project file exists
            if not os.path.exists(os.path.join(directory, 'TheProject.xpr')):
                shutil.rmtree(directory)
            else:
                new_hash = cls.predict_hash(
                    design_builders=design_builders,
                    simulation_builders=simulation_builders,
                    parameters=parameters,
                    temp_directory=os.path.join(directory, 'temp'),
                    directory=directory,
                )
                old_hash = cls.read_hash(directory)
                if new_hash != old_hash:
                    logger.debug('Project has changed {}->{}.  Deleting and regenerating.'.format(old_hash, new_hash))
                    shutil.rmtree(directory)
                else:
                    logger.debug('Project has not changed since last time.')
            
    @classmethod
    def create(cls, design_builders, simulation_builders, parameters, directory,
               tasks_collection=None, part='', board='', top_module=''):
        '''
        Create a new Vivado project from `Builder`'s specifying the top level
        modules.  Spawns a Viavdo process to create the project and returns a 
        python wrapper around the process while that process is still running in
        the background.

        Args:
            `design_builders`: The builders responsible for the synthesizable code.
            `simulation_builders`: The builders responsible for the simulation code.
            `parameters`: Top level parameters used to generated the design.  Must include
                'factory_name' which will be used to find the `interface` for test bench
                projects that read the parameters and the `comm` for fpga projects. 
            `temp_directory`: We temporary directory where we'll generate the files
                so we can work out the hash.
            `directory`: The real project location.  This is required since some
                simulation files may need this information.
            `tasks_collection`: How we keep track of Vivado processes.
            `part`: The 'part' to use when implementing.
            `board`: The 'board' to use when implementing.
            `top_module`: The top level module in the design.
        '''
        
        cls.write_params(params=parameters, directory=directory)
        design_requirements = builder.build_all(
            directory, top_builders=design_builders, top_params=parameters)
        simulation_requirements = builder.build_all(
            directory, top_builders=simulation_builders, top_params=parameters)
        ips = builder.condense_ips(
            design_requirements['ips'] + simulation_requirements['ips'])
        p = super().create(
            directory=directory,
            design_files=design_requirements['filenames'],
            simulation_files=simulation_requirements['filenames'],
            tasks_collection=tasks_collection,
            ips=ips,
            board=board,
            part=part,
            top_module=top_module,
        )
        return p

    @classmethod
    def create_or_update(cls, design_builders, simulation_builders, parameters, directory,
               tasks_collection=None, part='', board='', top_module=''):
        '''
        Create a new BuilderProject if one does not already exist in the 
        directory.  If one does exist and the dependencies have been modified
        then delete the old project and create a new one.  If one does exist
        and the dependencies have not been modified then use the existing
        project.
        '''
        if os.path.exists(directory):
            cls.delete_if_changed(
                design_builders=design_builders,
                simulation_builders=simulation_builders,
                parameters=parameters,
                directory=directory,
                tasks_collection=tasks_collection,
                part=part,
                board=board,
                top_module=top_module,
            )
        if os.path.exists(directory):
            logger.debug('Using old Project.')
            p = cls(directory=directory, tasks_collection=tasks_collection)
        else:
            logger.debug('Making new Project.')
            os.makedirs(directory)
            p = cls.create(
                design_builders=design_builders,
                simulation_builders=simulation_builders,
                parameters=parameters,
                directory=directory,
                tasks_collection=tasks_collection,
                part=part,
                board=board,
                top_module=top_module,
            )
            t = p.wait_for_most_recent_task()
            errors = t.get_errors()
            assert(len(errors) == 0)
        return p

    def read_params(self):
        '''
        Read the parameters that were used to generate this project.
        '''
        fn = os.path.join(self.directory, 'params.txt')
        with open(fn, 'r') as f:
            params = json.load(f)
        return params

    @classmethod
    def params_text(cls, params):
        if 'factory_name' not in params:
            raise ValueError('Parameters used to create a BuilderProject must contain a "factory_name"')
        as_json = json.dumps(params, sort_keys=True,
                             indent=2, separators=(',', ': '))
        return as_json

    @classmethod
    def write_params(cls, params, directory):
        '''
        Write the parameters that were used to generate this project.
        '''
        fn = os.path.join(directory, 'params.txt')
        if os.path.exists(fn):
            raise Exception('Parameters file already exists.')
        as_json = cls.params_text(params)
        with open(fn, 'w') as f:
            f.write(as_json)


class FPGAProject(BuilderProject):
    '''
    A python wrapper around a Vivado project that is designed to be deployed
    to the FPGA and communicated with over JTAG and the JTAG-to-AXI block.
    '''

    @classmethod
    def make_parent_params(
            cls, the_builder, parameters, directory,
            tasks_collection=None, part='', board=''):
        '''
        Takes the top level builder (which must have an AXI4Lite interface) along
        with the project parameters and generate the parameters required by
        `BuilderProject.create`.
        '''
        parameters['board_params'] = boards.get_board_params(board)
        jtagaxi_builder = jtag_axi_wrapper.JtagAxiWrapperBuilder(parameters)
        return {
            'design_builders': [the_builder, jtagaxi_builder],
            'simulation_builders': [],
            'parameters': parameters,
            'directory': directory,
            'tasks_collection': tasks_collection,
            'part': part,
            'board': board,
        }

    @classmethod
    def create_or_update(
            cls, the_builder, parameters, directory,
            tasks_collection=None, part='', board=''):
        '''
        Create a new FPGAProject if one does not already exist in the 
        directory.  If one does exist and the dependencies have been modified
        then delete the old project and create a new one.  If one does exist
        and the dependencies have not been modified then use the existing
        project.

        Args: 
            `the_builder`: The builder for the top level module with an AXI4Lite
                 interface.
            `parameters`: The top level parameters for the design.  These are
                 passed the builders of any packages required. 
            `directory`: The directory where the project will be created.
            `tasks_collection`: How to keep track of the Vivado processes we start.
            `part`: The 'part' to use when implementing.
            `board`: The 'board' to used when implementing.
        '''
        parent_params = cls.make_parent_params(
            the_builder=the_builder, parameters=parameters, directory=directory,
            tasks_collection=tasks_collection, part=part, board=board)
        if os.path.exists(directory):
            cls.delete_if_changed(**parent_params)
        if os.path.exists(directory):
            logger.debug('Using old Project.')
            p = cls(directory=directory, tasks_collection=tasks_collection)
        else:
            logger.debug('Making new Project.')
            os.makedirs(directory)
            p = super().create(**parent_params)
            t = p.wait_for_most_recent_task()
            errors = t.get_errors()
            assert(len(errors) == 0)
        return p

    def get_monitors_hwcode(self, monitor_task):
        '''
        Get the hardware code for the FPGA that this project has been deployed to.
        '''
        # Wait for the monitor to become available.
        max_waits = 60
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
        description = 'Monitor Redis connection and pass command to FPGA.'
        t = task.VivadoTask.create(
            parent_directory=self.directory,
            command_text='::pyvivado::monitor_redis {} 0'.format(hwcode),
            description=description,
            tasks_collection=self.tasks_collection,
        )
        t.run()
        hwcode = self.get_monitors_hwcode(t)
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
        hwcode = redis_utils.get_free_hwcode()
        if hwcode is None:
            raise Exception('No free hardware found.')
        # Spawn a Vivado process to deploy the bitstream and
        # start monitoring.
        t = task.VivadoTask.create(
            parent_directory=self.directory,
            command_text='::pyvivado::send_to_fpga_and_monitor {{{}}} {} {}'.format(
                self.directory, hwcode, fake_int),
            description=description,
            tasks_collection=self.tasks_collection,
        )
        t.run()
        # Wait for the task to start monitoring and get the
        # hardware code of the free fpga.
        hwcode = self.get_monitors_hwcode(t)
        # Create a Connection object for communication with the FPGA/
        conn = connection.Connection(hwcode)
        return t, conn


class FileTestBenchProject(BuilderProject):
    '''
    A python wrapper around a Vivado project that will run verification by
    reading inputs from files and writing outputs to files.
    '''

    @classmethod
    def make_parent_params(cls, interface, directory, tasks_collection=None,
                           part='', board=''):
        '''
        Takes an `Interface` object for the module we are testing and
        generates the parameters required by `BuilderProject.create`.
        '''
        inner_wrapper_builder = inner_wrapper.InnerWrapperBuilder({
            'interface': interface,
        })
        file_testbench_builder = file_testbench.FileTestbenchBuilder({
            'interface': interface,
        })
        interface.parameters['factory_name'] = interface.factory_name
        return {
            'design_builders': [inner_wrapper_builder, interface.builder],
            'simulation_builders': [file_testbench_builder],
            'parameters': interface.parameters,
            'directory': directory,
            'tasks_collection': tasks_collection,
            'part': part,
            'board': board,
            'top_module': 'FileTestBench',
        }
            
    @classmethod
    def create_or_update(cls, interface, directory, tasks_collection=None,
                         part='', board=''):
        '''
        Create a new FileTestBenchProject if one does not already exist in the 
        directory.  If one does exist and the dependencies have been modified
        then delete the old project and create a new one.  If one does exist
        and the dependencies have not been modified then use the existing
        project.

        Args: 
            `interface`: The `Interface` object for the top level module.
            `directory`: The directory where the project will be created.
            `tasks_collection`: How to keep track of the Vivado processes we start.
            `part`: The 'part' to use when implementing.
            `board`: The 'board' to used when implementing.
        '''        
        parent_params = cls.make_parent_params(
            interface=interface, directory=directory,
            tasks_collection=tasks_collection, part=part, board=board)
        if os.path.exists(directory):
            super().delete_if_changed(**parent_params)
        if os.path.exists(directory):
            logger.debug('Using old Project.')
            p = cls(directory=directory, tasks_collection=tasks_collection)
        else:
            logger.debug('Making new Project.')
            os.makedirs(directory)
            p = super().create(**parent_params)
            t = p.wait_for_most_recent_task()
            errors = t.get_errors()
            assert(len(errors) == 0)
        return p
                
    def __init__(self, directory, tasks_collection=None):
        '''
        Create a python wrapper around an existing Vivado testbench project.
        '''
        self.input_filename = os.path.join(directory, 'input.data')
        self.output_filename = os.path.join(directory, 'output.data')
        super().__init__(directory, tasks_collection)
        self.params = self.read_params()
        # We regenerate the interface object based on the parameters
        # file that was written when the project was created.
        self.interface = interface.module_register[self.params['factory_name']](
            params=self.params)

    def run_simulation(self, input_data, runtime=None, sim_type='hdl'):
        '''
        Spawns a vivado process that will run of simulation of the project.

        Args:
            `input_data`: A list of dictionaries of the input wire values.
            `runtime`: A string specifying the runtime.
            'sim_type`: The string specifying the simulation type.  It can be
               'hdl', 'post_synthesis', or 'timing.

        Returns a (errors, output_data) tuple where:
            `errors`: If a list of errors produced by the simulation task.
            `output_data`: A list of dictionaries of the output wire values.
        '''
        command_template = '''
open_project {{{project_filename}}}
::pyvivado::run_{sim_type}_simulation {{{directory}}} {{{runtime}}}
'''
        if runtime is None:
            runtime = '{} ns'.format((len(input_data) + 20) * 10)
        command = command_template.format(
            project_filename=self.filename, runtime=runtime, sim_type=sim_type,
            directory=self.directory) 
        # Create a task to run the simulation.
        t = task.VivadoTask.create(
            parent_directory=self.directory,
            description='Running a HDL simulation.',
            command_text=command,
            tasks_collection=self.tasks_collection,
        )
        # Write the input file to the task directory.
        self.interface.write_input_file(
            input_data, os.path.join(t.directory, self.input_filename))
        # Run the simulation task and wait for it to complete.
        t.run_and_wait()
        errors = t.get_errors()
        # Write the output files.
        data_out = self.interface.read_output_file(
            os.path.join(t.directory, self.output_filename))
        return errors, data_out

