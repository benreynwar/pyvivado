import os
import logging

from pyvivado import interface, signal, config, builder, utils
from pyvivado.hdl.wrapper import dummy_wrapper
from pyvivado.hdl import pyvivado_utils

logger = logging.getLogger(__name__)

class InnerWrapperBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.interface = params['interface']
        self.language = self.interface.language
        signals_in = []
        for wire_name, wire_type in self.interface.wires_in:
            signal = {
                'name': wire_name,
                'from_slv': wire_type.conversion_from_slv(
                    'idw_slv_' + wire_name),
                'sv_from_slv': wire_type.sv_conversion_from_slv(
                    'idw_slv_' + wire_name),
                'width': wire_type.width,
                'typ': wire_type.typ(),
                'sv_typ': wire_type.sv_typ('idw_'+wire_name), 
                'direction': 'in',
            }
            signals_in.append(signal)
        signals_out = []
        for wire_name, wire_type in self.interface.wires_out:
            signal = {
                'name': wire_name,
                'to_slv': wire_type.conversion_to_slv(
                    'idw_' + wire_name),
                'sv_to_slv': wire_type.sv_conversion_to_slv(
                    'idw_' + wire_name),
                'width': wire_type.width, 
                'typ': wire_type.typ(),
                'sv_typ': wire_type.sv_typ('idw_'+wire_name),
                'direction': 'out',
            }
            signals_out.append(signal)
        self.template_params = {
            'signals_in': signals_in,
            'signals_out': signals_out,
            'port_signals': [],
            'dut_name': self.interface.module_name,
            'wrapped_module_name': self.interface.wrapped_module_name,
            'dut_parameters': self.interface.module_parameters,
            'clock_names': self.interface.clock_names,
            'packages': self.interface.packages,
        }
        if self.interface.needs_dummy:
            self.builders = [
                dummy_wrapper.DummyWrapperBuilder(self.template_params),
                self.interface.builder,
            ]
        else:
            self.builders = [
                self.interface.builder,
            ]
        self.packages = [
            'pyvivado_utils',
            #'pyvivado_utils_sv',
        ]
        
    def get_filename(self, directory):
        if self.language == 'vhdl':
            fn = os.path.join(directory, 'inner_wrapper.vhd')
        elif self.language in ('systemverilog', 'verilog'):
            fn = os.path.join(directory, 'inner_wrapper.sv')
        else:
            raise ValueError('Unknown language: {}'.format(self.language))
        return fn

    def build(self, directory):
        if self.language == 'vhdl':
            template_fn = os.path.join(config.hdldir, 'wrapper', 'inner_wrapper.vhd.t')
        elif self.language in ('systemverilog', 'verilog'):
            template_fn = os.path.join(config.hdldir, 'wrapper', 'inner_wrapper.sv.t')
        else:
            raise ValueError('Unknown language: {}'.format(self.language))            
        output_fn = self.get_filename(directory)
        utils.format_file(template_fn, output_fn, self.template_params)
        
    def required_filenames(self, directory):
        return [
            self.get_filename(directory),
        ]

    def required_packages(self):
        # Assumes that we can just remove 'work.' to get package name.
        return [p[len('work.'):] for p in self.interface.packages]
