import os
import logging

from pyvivado import tasks_collection, config, utils
from pyvivado import shell_task

logger = logging.getLogger(__name__)


class VCSProject(object):
    '''
    The base class for python wrappers around VCS Projects.
    '''

    def __init__(self, project):
        '''
        Create a new VCS project.

        Args:
            `project`: A BaseProject that we want to create a VCS project based upon.
        '''
        self.project = project
        self.directory = self.directory_from_project(project)
        if not os.path.exists(self.directory):
            os.mkdir(self.directory)
        self.tasks_collection = tasks_collection.TasksCollection(
            self.directory, task_type=shell_task.ShellTask)

    @classmethod
    def directory_from_project(cls, project):
        return os.path.join(project.directory, 'vcs')

    def make_simulation_task(self, test_name, sim_type='hdl'):
        if sim_type == 'post_synthesis':
            mapped_design_fn = os.path.join(self.directory, 'mapped_design.v')
            if not os.path.exists(mapped_design_fn):
                raise Exception('Cannot run post synthesis simulation if mapped design does not exist')
            design_files = [mapped_design_fn]
            top_sim_type = 'vcs_post_synthesis'
        elif sim_type == 'hdl':
            design_files = self.project.files_and_ip['design_files']
            top_sim_type = 'vcs_hdl'
        simulation_files = self.project.files_and_ip['simulation_files']
        vlog_design_files = [fn for fn in design_files
                             if (fn[-2:] == '.v' or fn[-3:] == '.sv')]
        vhd_design_files = [fn for fn in design_files
                            if (fn[-4:] == '.vhd')]
        ips = self.project.files_and_ip['ips']
        memories = []
        for ip_name, ip_params, ip_inst in ips:
            if ip_name == 'Memory':
                memories.append((ip_params['width'], ip_params['depth']))
            else:
                raise Exception('Unknown ip name: {}'.format(ip_name))
        wrapper_fn = os.path.join(self.directory, 'file_testbench_wrapper_.vhd'.format(top_sim_type))
        input_filename = self.project.get_input_filename(test_name)
        output_filename = self.project.get_output_filename(
            test_name=test_name, sim_type=top_sim_type)
        utils.format_file(
            template_filename=os.path.join(config.hdldir, 'wrapper', 'file_testbench_wrapped.vhd.t'),
            output_filename=wrapper_fn,
            parameters={
                'input_filename': input_filename,
                'output_filename': output_filename,
            },
        )
        top_module =self.project.files_and_ip['top_module']
        template_fn = os.path.join(config.shdir, 'run_{}.sh.t'.format(top_sim_type))
        command_fn = os.path.join(self.directory, 'run_{}_{}.sh'.format(top_sim_type, test_name))
        utils.format_file(
            template_filename=template_fn,
            output_filename=command_fn,
            parameters={
                'vlog_design_files': vlog_design_files,
                'vhd_design_files': vhd_design_files,
                'simulation_files': simulation_files + [wrapper_fn],
                'top_module': top_module,
                'input_filename': input_filename,
                'output_filename': output_filename,
                'tcldir': config.tcldir,
            })
        # Create a task to run the simulation
        t = shell_task.ShellTask.create(
            collection=self.tasks_collection,
            description='Run VCS simulation.',
            command_text='bash {}'.format(command_fn),
        )
        return t

    def run_simulation(self, test_name, sim_type):
        t = self.make_simulation_task(test_name, sim_type)
        # Run the simulation task and wait for it to complete.
        t.run_and_wait()
        errors = t.get_errors()
        output_filename = self.project.get_output_filename(
            sim_type='vcs_{}'.format(sim_type), test_name=test_name)
        if not os.path.exists(output_filename):
            logger.error('Failed to create output file from simulation')
            data_out = []
        else:
            # Read the output files.
            data_out = self.project.interface.read_output_file(
                os.path.join(t.directory, output_filename))
        return errors, data_out

    def make_synthesis_task(self, tech, clock_period):
        design_files = self.project.files_and_ip['design_files']
        ips = self.project.files_and_ip['ips']
        tech_info = tech.get_info(ips)
        for name, dn in tech_info['libs_to_convert']:
            self.run_convert_lib(name, dn)
        if tech_info['use_physical']:
            command_text = 'dc_shell -topo -f dc_synthesis.tcl'
        else:
            command_text = 'dc_shell -f dc_synthesis.tcl'
        t = shell_task.ShellTask.create(
            collection=self.tasks_collection,
            description='Run dc_shell synthesis',
            command_text=command_text,
        )
        # Make the .synopsys_dc.setup file
        # At the moment we're putting it in the vcs directory instead of the
        # task directory.  This will cause problems if we want different tasks
        # with different setup files.
        utils.format_file(
            template_filename=os.path.join(config.tcldir, 'synopsys_dc.setup.t'),
            output_filename=os.path.join(t.directory, '.synopsys_dc.setup'),
            parameters={
                'additional_search_path': ' '.join(tech_info['additional_search_paths']),
                'target_library': ' '.join(tech_info['target_library']),
                'symbol_library': tech_info['symbol_library'],
            },
        )
        # Make the load design script.
        command_fn = os.path.join(t.directory, 'dc_synthesis.tcl')
        utils.format_file(
            template_filename=os.path.join(config.tcldir, 'dc_synthesis.tcl.t'),
            output_filename=command_fn,
            parameters={
                'design_files': design_files,
                'top_module': 'InsideDutWrapper',
                'clock_period': clock_period,
                'clock_uncertainty': 0.1,
                'clock_transition': 0.05,
                },
            )
        return t

    def run_synthesis(self, tech, clock_period):
        t = self.make_synthesis_task(tech, clock_period)
        t.run_and_wait()
        errors = t.get_errors()
        return errors

    def make_convert_lib_task(self, name, dn):
        t = shell_task.ShellTask.create(
            collection=self.tasks_collection,
            description='Convert .lib to .db',
            command_text='lc_shell -f convert.tcl',
        )
        lib_fn = os.path.join(dn, name + '.lib')
        db_fn = os.path.join(dn, name + '.db')
        tcl_template = '''
read_lib {}
write_lib {}_lib -f db -o {}
exit'''.format(lib_fn, name, db_fn)
        tcl_fn = os.path.join(t.directory, 'convert.tcl')
        with open(tcl_fn, 'w') as f:
            f.write(tcl_template)
        return t

    def run_convert_lib(self, name, dn):
        t = self.make_convert_lib_task(name, dn)
        t.run_and_wait()
        errors = t.get_errors()
        return errors

