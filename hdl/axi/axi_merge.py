import os
import logging
import math
import random

from pyvivado import interface, signal, builder, utils, config, axi

from pyvivado.hdl.axi import axi_utils

logger = logging.getLogger(__name__)
class AxiMergeBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.simple_filenames = [
            os.path.join(config.hdldir, 'axi', 'axi_merge.vhd'),
        ]
        self.packages = [
            'axi_utils',
        ]

def get_axi_merge_interface(params):
    n_masters = params['n_masters']
    module_name = 'axi_merge'
    builder = AxiMergeBuilder({})
    module_parameters = {
        'n_masters': n_masters,
    }
    wires_in = (
        ('reset', signal.std_logic_type),
        ('i_s', axi.axi4lite_s2m_type),
        ('i_m', signal.Array(contained_type=axi.axi4lite_m2s_type,
                             size=n_masters)),
    )
    wires_out = (
        ('o_s', axi.axi4lite_m2s_type),
        ('o_m', signal.Array(contained_type=axi.axi4lite_s2m_type,
                             size=n_masters)),
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


class AxiMerge(object):

    def __init__(self, n_masters):
        self.n_masters = n_masters
        self.reset()

    def reset(self):
        self.active_master_index = 0
        self.waiting_for_write_response = False
        self.waiting_for_read_response = False

    def process(self, inputs):
        am_inputs = inputs['i_m'][self.active_master_index]
        s_inputs = inputs['i_s']
        waiting = self.waiting_for_write_response or self.waiting_for_read_response
        m_outputs = []
        # Produce responses to master
        for mi in range(self.n_masters):
            s2m = axi.make_empty_axi4lite_s2m_dict()
            s2m['bresp'] = s_inputs['bresp']
            s2m['rresp'] = s_inputs['rresp']
            s2m['rdata'] = s_inputs['rdata']
            s2m['arready'] = 0
            s2m['awready'] = 0
            s2m['wready'] = 0
            if mi == self.active_master_index:
                s2m['bvalid'] = s_inputs['bvalid']
                s2m['rvalid'] = s_inputs['rvalid']
                if not waiting:
                    s2m['arready'] = 1
                    s2m['awready'] = 1
                    s2m['wready'] = 1
            m_outputs.append(s2m)
        # Produce command to slave
        s_output = axi.make_empty_axi4lite_m2s_dict()
        if not waiting:
            s_output['awvalid'] = am_inputs['awvalid']
            s_output['arvalid'] = am_inputs['arvalid']
            s_output['wvalid'] = am_inputs['wvalid']
            s_output['rready'] = 0
            s_output['bready'] = 0
        else:
            s_output['awvalid'] = 0
            s_output['arvalid'] = 0
            s_output['wvalid'] = 0
        if self.waiting_for_read_response:
            s_output['rready'] = 1
        else:
            s_output['rready'] = 0
        if self.waiting_for_write_response:
            s_output['bready'] = 1
        else:
            s_output['bready'] = 0
        s_output['awaddr'] = am_inputs['awaddr']
        s_output['araddr'] = am_inputs['araddr']
        s_output['wdata'] = am_inputs['wdata']

        outputs = {
            'o_m': m_outputs,
            'o_s': s_output,
        }
            
        if inputs['reset']:
            self.reset()
        else:
            if not waiting:
                if am_inputs['awvalid']:
                    self.waiting_for_write_response = True
                if am_inputs['arvalid']:
                    self.waiting_for_read_response = True
                if not (am_inputs['awvalid'] or am_inputs['arvalid']):
                    self.active_master_index = (self.active_master_index + 1) % self.n_masters
            else:
                if s_inputs['bvalid']:
                    self.waiting_for_write_response = False
                if s_inputs['rvalid']:
                    self.waiting_for_read_response = False

        return outputs


name = 'axi_merge'
assert(name not in interface.module_register)
interface.module_register[name] = get_axi_merge_interface
assert(name not in builder.module_register)
builder.module_register[name] = AxiMergeBuilder

