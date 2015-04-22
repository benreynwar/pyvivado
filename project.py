import os
import fnmatch
import logging
import time
import json
import hashlib
import shutil

from pyvivado import config, task, utils, interface, builder, redis_utils, sqlite_collection
from pyvivado.hdl.wrapper import inner_wrapper, file_testbench

logger = logging.getLogger(__name__)

def params_text(params):
    as_json = json.dumps(params, sort_keys=True,
                         indent=2, separators=(',', ': '))
    return as_json


class Project(object):
    
    @classmethod
    def default_tasks_collection(cls, directory):
        db_fn = os.path.join(directory, 'tasks.db')
        tasks_collection = sqlite_collection.SQLLiteCollection(db_fn)        
        return tasks_collection

    @staticmethod
    def hash(design_files, simulation_files, ips):
        h = hashlib.sha1()
        h.update(utils.files_hash(design_files))
        h.update(utils.files_hash(simulation_files))
        # FIXME: Not sure whether this will work properly for
        # the ips
        h.update(str(ips).encode('ascii'))
        return h.digest()

    @staticmethod
    def read_hash(directory):
        hash_fn = os.path.join(directory, 'hash.txt')
        if not os.path.exists(hash_fn):
            h = None
        else:
            with open(hash_fn, 'rb') as f:
                h = f.read()
        return h

    @staticmethod
    def write_hash(directory, h):
        hash_fn = os.path.join(directory, 'hash.txt')
        with open(hash_fn, 'wb') as f:
            f.write(h)

    @classmethod
    def create(cls, directory, design_files, simulation_files,
               tasks_collection=None,
               part='', board='', ips=[],
               top_module=''):
        if tasks_collection is None:
            tasks_collection = cls.default_tasks_collection(directory)
        tcl_ips = []
        for ip_name, ip_properties, module_name in ips:
            ip_version = ''
            tcl_start = '{ip_name} {{{ip_version}}} {module_name}'.format(
                ip_name=ip_name, ip_version=ip_version, module_name=module_name)
            tcl_properties = ' '.join(
                ['{{ {} {} }}'.format(k, v) for k,v in ip_properties.items()])
            tcl_ip = '{} {{ {} }}'.format(tcl_start, tcl_properties)
            tcl_ips.append(tcl_ip)
        tcl_ips = ' '.join(['{{ {} }}'.format(ip) for ip in tcl_ips])
        if os.path.exists(os.path.join(directory, 'TheProject.xpr')):
            raise Exception('Project already exists.')
        cls.write_hash(directory, cls.hash(
            design_files=design_files,
            simulation_files=simulation_files,
            ips=ips,
        ))
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
        p = cls(directory, tasks_collection)
        return p
    
    def __init__(self, directory, tasks_collection=None):
        self.directory = directory
        if tasks_collection is None:
            self.tasks_collection = self.default_tasks_collection(directory)
        else:
            self.tasks_collection = tasks_collection
        self.filename = os.path.join(directory, 'TheProject.xpr')
        
    def get_tasks(self):
        ids = [int(fn[5:]) for fn in os.listdir(self.directory)
               if fnmatch.fnmatch(fn, 'task_*')]
        tasks = [
            task.VivadoTask(_id=_id, tasks_collection=self.tasks_collection)
            for _id in ids]
        return tasks

    def unfinished_tasks(self):
        tasks = [t for t in self.get_tasks() if not t.is_finished()]
        return tasks

    def get_most_recent_task(self):
        ids = [int(fn[5:]) for fn in os.listdir(self.directory)
               if fnmatch.fnmatch(fn, 'task_*')]
        ids.sort()
        t = task.VivadoTask(_id=ids[0], tasks_collection=self.tasks_collection)
        return t

    def wait_for_most_recent_task(self):
        t = self.get_most_recent_task()
        while not t.is_finished():
            logger.debug('Waiting for tasks to finish.')
            time.sleep(1)
        t.log_messages(t.get_messages())
        return t


class BuilderProject(Project):

    @classmethod
    def delete_if_changed(
            cls, design_builders, simulation_builders, parameters, directory):
        if os.path.exists(directory):
            # The project exists so we need to check if files and ip have
            # changed.
            # Make a new directory for temporary files.
            temp_dir = os.path.join(directory, 'temp')
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            design_requirements = builder.build_all(
                temp_dir, top_builders=design_builders, top_params=parameters)
            simulation_requirements = builder.build_all(
                temp_dir, top_builders=simulation_builders,
                top_params=parameters)
            ips = builder.condense_ips(
                design_requirements['ips'] + simulation_requirements['ips'])
            new_hash = cls.hash(
                design_files=design_requirements['filenames'],
                simulation_files=simulation_requirements['filenames'],
                ips=ips)
            old_hash = cls.read_hash(directory)
            if new_hash != old_hash:
                logger.debug('Project has changed {}->{}.  Deleting and regenerating.'.format(old_hash, new_hash))
                shutil.rmtree(directory)

    @classmethod
    def create(cls, design_builders, simulation_builders, parameters, directory,
               tasks_collection=None, part='', board='', top_module=''):
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

    def read_params(self):
        fn = os.path.join(self.directory, 'params.txt')
        with open(fn, 'r') as f:
            params = json.load(f)
        return params

    def write_params(params, factory_name, directory):
        fn = os.path.join(directory, 'params.txt')
        params['factory_name'] = factory_name
        if os.path.exists(fn):
            raise Exception('Parameters file already exists.')
        as_json = json.dumps(params, sort_keys=True,
                             indent=2, separators=(',', ': '))
        with open(fn, 'w') as f:
            f.write(as_json)
                

class FPGAProject(BuilderProject):

    def create(cls, the_builder, parameters, directory,
               tasks_collection=None,
               part='', board=''):
        p = super().create(
            directory=directory,
            design_builders=[the_builder],
            simulation_builders=[],
            parameters=parameters,
            tasks_collection=tasks_collection,
            board=board,
            part=part,
        )
        return p
        
    def send_to_fpga_and_monitor(self):
        hwcode = redis_utils.get_free_hwcode()
        if hwcode is None:
            raise StandardException('No free hardware found.')
        t = task.VivadoTask.create(
            parent_directory=self.directory,
            command_text='::pyvivado::send_to_fpga_and_monitor {{{}}} {}'.format(
                self.directory, hwcode),
            description='Sending project to fpga and monitoring.',
            tasks_collection=self.tasks_collection,
        )
        t.run()
        return t

    def implement(self):
        t = task.VivadoTask.create(
            parent_directory=self.directory,
            command_text='::pyvivado::open_and_implement {{{}}}'.format(
                self.directory),
            description='Implement project.',
            tasks_collection=self.tasks_collection,
        )
        t.run()
        return t
        

class FileTestBenchProject(BuilderProject):

    @classmethod
    def delete_if_changed(cls, interface, directory):
        inner_wrapper_builder = inner_wrapper.InnerWrapperBuilder({
            'interface': interface,
        })
        file_testbench_builder = file_testbench.FileTestbenchBuilder({
            'interface': interface,
        })
        super().delete_if_changed(
            directory=directory,
            design_builders=[inner_wrapper_builder, interface.builder],
            simulation_builders=[file_testbench_builder],
            parameters=interface.parameters,
        )

    @classmethod
    def create_or_update(cls, interface, directory,
               tasks_collection=None,
               part='', board=''):
        if os.path.exists(directory):
            cls.delete_if_changed(interface=interface, directory=directory)
        if os.path.exists(directory):
            p = cls(directory=directory, tasks_collection=tasks_collection)
        else:
            os.makedirs(directory)
            p = cls.create(
                interface=interface,
                directory=directory,
                tasks_collection=tasks_collection,
                part=part,
                board=board,
            )
        return p
                

    @classmethod
    def create(cls, interface, directory,
               tasks_collection=None,
               part='', board=''):
        inner_wrapper_builder = inner_wrapper.InnerWrapperBuilder({
            'interface': interface,
        })
        file_testbench_builder = file_testbench.FileTestbenchBuilder({
            'interface': interface,
        })
        cls.write_params(interface.parameters, interface.factory_name, directory)
        p = super().create(
            directory=directory,
            design_builders=[inner_wrapper_builder, interface.builder],
            simulation_builders=[file_testbench_builder],
            tasks_collection=tasks_collection,
            board=board,
            part=part,
            top_module='FileTestBench',
            parameters=interface.parameters,
        )
        return p

    def __init__(self, directory, tasks_collection=None):
        self.input_filename = os.path.join(directory, 'input.data')
        self.output_filename = os.path.join(directory, 'output.data')
        super().__init__(directory, tasks_collection)
        self.params = self.read_params()
        self.interface = interface.module_register[self.params['factory_name']](
            params=self.params)

    def run_simulation(self, input_data, runtime, sim_type='hdl'):
        command_template = '''
open_project {{{project_filename}}}
::pyvivado::run_{sim_type}_simulation {{{runtime}}}
'''
        command = command_template.format(
            project_filename=self.filename, runtime=runtime, sim_type=sim_type) 
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
        t.run_and_wait()
        errors = t.get_errors()
        data_out = self.interface.read_output_file(
            os.path.join(t.directory, self.output_filename))
        return errors, data_out

    
