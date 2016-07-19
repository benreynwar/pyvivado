import os
import logging
import filecmp

from pyvivado.base_project import BuilderProject
from pyvivado.interface import module_register

from pyvivado.hdl.wrapper import inner_wrapper, file_testbench

# To load into registry
from pyvivado.hdl import pyvivado_utils

logger = logging.getLogger(__name__)


class FileTestBenchProject(BuilderProject):
    '''
    A python wrapper around a Vivado project that will run verification by
    reading inputs from files and writing outputs to files.
    '''

    @classmethod
    def make_parent_params(cls, directory, interface):
        '''
        Takes an `Interface` object for the module we are testing and
        generates the parameters required by `BuilderProject.create`.
        '''
        interface.parameters['factory_name'] = interface.factory_name
        inner_wrapper_builder = inner_wrapper.InnerWrapperBuilder(interface.parameters)
        file_testbench_builder = file_testbench.FileTestbenchBuilder(interface.parameters)
        return {
            'design_builders': [inner_wrapper_builder, interface.builder],
            'simulation_builders': [file_testbench_builder],
            'top_module': 'FileTestBench',
            'parameters': interface.parameters,
            'directory': directory,
        }

    def __init__(self, directory, interface=None, params=None,
                 overwrite_ok=False, exclude_fn=None, additional_files=[]):
        '''
        Create a python wrapper around an existing Vivado testbench project.
        '''
        if (params is not None) or (interface is not None):
            if interface is None:
                interface = module_register[params['factory_name']](params)
            parent_params = self.make_parent_params(
                interface=interface,  directory=directory)
            super().__init__(overwrite_ok=overwrite_ok, exclude_fn=exclude_fn,
                             additional_files=additional_files, **parent_params)
            self.interface = interface
        else:
            super().__init__(directory=directory, overwrite_ok=overwrite_ok)
            self.params = self.read_params()
            # We regenerate the interface object based on the parameters
            # file that was written when the project was created.
            self.interface = interface.module_register[self.params['factory_name']](
                params=self.params)

    def get_input_filename(self, test_name):
        directory = os.path.join(self.directory, test_name)
        input_data_fn = os.path.join(directory, 'input.data')
        return input_data_fn

    def update_input_data(self, test_name, input_data):
        '''
        Update the input data and return whether it changed.
        '''
        directory = os.path.join(self.directory, test_name)
        if not os.path.exists(directory):
            os.mkdir(directory)
        input_data_fn = self.get_input_filename(test_name=test_name)
        old_input_data_fn = os.path.join(directory, 'old_input.data')
        if os.path.exists(old_input_data_fn):
            os.remove(old_input_data_fn)
        if os.path.exists(input_data_fn):
            os.rename(input_data_fn, old_input_data_fn)
        self.interface.write_input_file(input_data, input_data_fn)
        if os.path.exists(old_input_data_fn):
            is_changed = not filecmp.cmp(input_data_fn, old_input_data_fn)
        else:
            is_changed = True
        return is_changed

    def get_output_filename(self, test_name, sim_type):
        directory = os.path.join(self.directory, test_name)
        return os.path.join(directory, '{}_output.data'.format(sim_type))
