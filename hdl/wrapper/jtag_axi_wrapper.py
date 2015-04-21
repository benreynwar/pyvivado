import os

from pyvivado import builder, config, utils

class JtagAxiWrapperBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params, package_name='JtagAxiWrapper')
        self.top_name = params['top_name']
        self.top_parameters = params.get('top_parameters', {})
        self.packages = [
            'axi_utils',
            params['top_name'],
        ]
        self.ips = [
            ('clk_wiz', (
                ('PRIM_IN_FREQ', 200),
                ('PRIM_SOURCE', 'Differential_clock_capable_pin'),
                ('CLKOUT1_REQUESTED_OUT_FREQ', params['frequency']),
            ), 'clk_wiz_0'),
            ('jtag_axi', (
                ('PROTOCOL', 2),
            ) , 'jtag_axi_0'),
        ]

    def get_filename(self, directory):
        return os.path.join(directory, 'jtag_axi_wrapper.vhd')

    def build(self, directory):
        template_filename = os.path.join(config.hdldir, 'wrapper', 'jtag_axi_wrapper.vhd.t')
        filename = self.get_filename(directory)
        params = {
            'dut_name': self.top_name,
            'dut_parameters': self.top_parameters,
        }
        utils.format_file(template_filename, filename, params)
        
    def required_filenames(self, directory):
        return [
            self.get_filename(directory),
            os.path.join(config.hdldir, 'wrapper', 'jtag_axi_wrapper.xdc')
        ]

builder.package_register['JtagAxiWrapper'] = JtagAxiWrapperBuilder
