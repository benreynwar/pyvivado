import os
import logging
import shutil

from pyvivado import boards, tasks_collection, hash_helper, config, utils
from pyvivado import params_helper, shell_task

logger = logging.getLogger(__name__)


class VCSProject(object):
    '''
    The base class for python wrappers around VCS Projects.
    '''

    def __init__(self, project):
        '''
        Create a new VCS project.

        Args:
            `project`: A BaseProject that we want to create a vivado project based upon.
        '''
        logger.debug('Init vivado project.')
        self.project = project
        self.directory = self.directory_from_project(project)
        if not os.path.exists(self.directory):
            os.mkdir(self.directory)
        self.tasks_collection = tasks_collection.TasksCollection(
            self.directory, task_type=shell_task.ShellTask)

    @classmethod
    def directory_from_project(cls, project):
        return os.path.join(project.directory, 'vcs')

    def make_hdl_simulation_task(self, test_name):
        design_files = self.project.files_and_ip['design_files']
        simulation_files = self.project.files_and_ip['simulation_files']
        ips = self.project.files_and_ip['ips']
        if ips:
            raise ValueError('VCS simulation in pyvivado assumes not ip blocks.')
        wrapper_fn = os.path.join(self.directory, 'file_testbench_wrapper.vhd')
        input_filename = self.project.get_input_filename(test_name)
        output_filename = self.project.get_output_filename(
            test_name=test_name, sim_type='vcs_hdl')
        utils.format_file(
            template_filename=os.path.join(config.hdldir, 'wrapper', 'file_testbench_wrapped.vhd.t'),
            output_filename=wrapper_fn,
            parameters={
                'input_filename': input_filename,
                'output_filename': output_filename,
            },
        )
        top_module =self.project.files_and_ip['top_module']
        template_fn = os.path.join(config.shdir, 'run_vcs_hdl.sh.t')
        command_fn = os.path.join(self.directory, 'run_vcs_hdl_{}.sh'.format(test_name))
        utils.format_file(
            template_filename=template_fn,
            output_filename=command_fn,
            parameters={
                'design_files': design_files,
                'simulation_files': simulation_files + [wrapper_fn],
                'top_module': top_module,
                'input_filename': input_filename,
                'output_filename': output_filename,
            })
        # Create a task to run the simulation
        t = shell_task.ShellTask.create(
            collection=self.tasks_collection,
            description='Run VCS simulation.',
            command_text='bash {}'.format(command_fn),
        )
        return t

    def run_hdl_simulation(self, test_name):
        t = self.make_hdl_simulation_task(test_name)
        # Run the simulation task and wait for it to complete.
        t.run_and_wait()
        errors = t.get_errors()
        output_filename = self.project.get_output_filename(
            sim_type='vcs_hdl', test_name=test_name)
        if not os.path.exists(output_filename):
            logger.error('Failed to create output file from simulation')
            data_out = []
        else:
            # Read the output files.
            data_out = self.project.interface.read_output_file(
                os.path.join(t.directory, output_filename))
        return errors, data_out
