import os
import logging

from pyvivado import builder, config

from pyvivado.hdl.axi import axi_utils

logger = logging.getLogger(__name__)


class AxiFailBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.simple_filenames = [
            os.path.join(config.hdldir, 'axi', 'axi_fail.vhd'),
        ]
        self.packages = [
            'axi_utils',
        ]

