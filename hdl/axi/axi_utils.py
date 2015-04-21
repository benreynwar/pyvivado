import os

from pyvivado import signal, config, builder

class AxiUtilsBuilder(builder.Builder):
    
    def __init__(self, params):
        super().__init__(params, package_name='axi_utils')
        self.simple_filenames = [
            os.path.join(config.hdldir, 'axi', 'axi_utils.vhd'),
        ]

assert('axi_utils' not in builder.package_register)
builder.package_register['axi_utils'] = AxiUtilsBuilder

