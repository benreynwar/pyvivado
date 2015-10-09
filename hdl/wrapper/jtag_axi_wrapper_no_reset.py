import os

from pyvivado import builder, config, utils
from pyvivado.hdl.wrapper import jtag_axi_wrapper

class JtagAxiWrapperNoResetBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params, package_name='JtagAxiWrapperNoReset')
        self.top_name = params['top_name']
        self.top_parameters = params.get('top_parameters', {})
        self.board_params = params['board_params']
        self.simple_filenames = [os.path.join(config.hdldir, 'wrapper', 'jtag_axi_wrapper_no_reset.vhd')]
        self.builders = [jtag_axi_wrapper.JtagAxiWrapperBuilder(params)]

builder.package_register['JtagAxiWrapperNoReset'] = JtagAxiWrapperNoResetBuilder
