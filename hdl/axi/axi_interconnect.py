import os
import logging

from pyvivado import interface, signal, builder, config, axi

# Import so it is available in register.
from pyvivado.hdl.axi import axi_utils

logger = logging.getLogger(__name__)


class AxiInterconnectBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.simple_filenames = [
            os.path.join(config.hdldir, 'axi', 'axi_interconnect.vhd'),
        ]
        self.packages = [
            'axi_utils',
        ]


def get_axi_interconnect_interface(params):
    module_name = 'axi_interconnect'
    slave_ids = params['slave_ids']
    max_n_slave_ids = 12 
    all_slave_ids = tuple(reversed(list(slave_ids) + [0] * (max_n_slave_ids - len(slave_ids))))
    builder = AxiInterconnectBuilder({})
    module_parameters = {
        'slave_ids': all_slave_ids,
        'n_slaves': len(slave_ids),
    }
    wires_in = (
        ('reset', signal.std_logic_type),
        ('i_m', axi.axi4lite_m2s_type),
        ('i_s', signal.Array(contained_type=axi.axi4lite_s2m_type,
                             size=len(slave_ids))),
    )
    wires_out = (
        ('o_m', axi.axi4lite_s2m_type),
        ('o_s', signal.Array(contained_type=axi.axi4lite_m2s_type,
                             size=len(slave_ids))),
    )
    packages = [
        'work.axi_utils',
    ]
    iface = interface.Interface(
        wires_in, wires_out, module_name=module_name,
        module_parameters=module_parameters,
        packages=packages,
        parameters=params, builder=builder, clock_names=['clk'],
    )
    return iface

name = 'axi_interconnect'
assert(name not in interface.module_register)
interface.module_register[name] = get_axi_interconnect_interface
assert(name not in builder.module_register)
builder.module_register[name] = AxiInterconnectBuilder

