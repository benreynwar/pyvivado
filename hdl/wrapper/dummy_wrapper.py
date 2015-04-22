import os
import logging

from pyvivado import interface, signal, config, builder, utils

logger = logging.getLogger(__name__)

class DummyWrapperBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.params = params
        
    def get_filename(self, directory):
        return os.path.join(directory, 'dummy_wrapper.vhd')

    def build(self, directory):
        template_fn = os.path.join(config.hdldir, 'wrapper', 'dummy_wrapper.vhd.t')
        output_fn = self.get_filename(directory)
        utils.format_file(template_fn, output_fn, self.params)
        
    def required_filenames(self, directory):
        return [
            self.get_filename(directory),
        ]
