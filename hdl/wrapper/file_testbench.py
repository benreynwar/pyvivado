import os
import logging

from pyvivado import config, builder, utils
from pyvivado.hdl.wrapper import outer_wrapper

logger = logging.getLogger(__name__)


class FileTestbenchBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.interface = params['interface']
        self.builders = [
            outer_wrapper.OuterWrapperBuilder(params),
        ]
        self.simple_filenames = [
            os.path.join(config.hdldir, 'pyvivado_utils.vhd'),
            os.path.join(config.hdldir, 'wrapper', 'clock.vhd'),
            os.path.join(config.hdldir, 'wrapper', 'txt_util.vhd'),
            os.path.join(config.hdldir, 'wrapper', 'read_file.vhd'),
            os.path.join(config.hdldir, 'wrapper', 'write_file.vhd'),
        ]

    def get_filename(self, directory):
        return os.path.join(directory, 'file_testbench.vhd')

    def build(self, directory):
        '''
        Produce the necessary files.
        `directory` is where the files will be placed.
        `false_directory` is where the files should think they are being placed.
        `false_directory` is necessary so we can compare the contents of files
        that have been placed in different directories when getting hashs.
        '''
        template_fn = os.path.join(config.hdldir, 'wrapper', 'file_testbench.vhd.t')
        output_fn = self.get_filename(directory)
        # Don't set a limit on running time
        time_limit = 0
        template_params = {
            'total_width_in': self.interface.total_width_in(),
            'total_width_out': self.interface.total_width_out(),
            'clock_period': '10 ns',
            'max_cycles': time_limit,
            'dut_parameters': self.interface.module_parameters,
        }
        utils.format_file(template_fn, output_fn, template_params)
        
    def required_filenames(self, directory):
        return self.simple_filenames + [
            self.get_filename(directory),
        ]

