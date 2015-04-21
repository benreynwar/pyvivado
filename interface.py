import os
import logging

from pyvivado import utils, config

logger = logging.getLogger(__name__)

module_register = {}

def add_to_module_register(name, get_interface_fn):
    if name in module_register:
        logger.warning('{} placed in module register twice (If this happens during testing probably OK because modules are sometimes imported twice.'.format(name))
    module_register[name] = get_interface_fn

class Interface(object): 
    
    def __init__(self, wires_in, wires_out, module_name, parameters,
                 builder, module_parameters={}, packages=[],
                 filenames=[], clock_names=[], factory_name=None,
                 needs_dummy=False, constants=[]):
        if factory_name is None:
            factory_name = module_name
        self.factory_name = factory_name
        self.wires_in = wires_in
        self.wires_out = wires_out
        self.clock_names = clock_names
        self.module_name = module_name
        self.parameters = parameters
        self.module_parameters = module_parameters
        self.packages = packages
        self.builder = builder
        self.filenames = filenames
        self.needs_dummy = needs_dummy
        self.wrapped_module_name = self.module_name
        self.constants = constants
        if needs_dummy:
            self.module_name = 'DummyDutWrapper'

    def total_width_in(self):
        width = 0
        for wire_name, wire_type in self.wires_in:
            width += wire_type.width
        return width

    def total_width_out(self):
        width = 0
        for wire_name, wire_type in self.wires_out:
            width+= wire_type.width
        return width

    def write_input_file(self, input_data, filename):
        lines = []
        for input_line in input_data:
            bitstrings = []
            for wire_name, wire_type in self.wires_in:
                if wire_name in input_line:
                    try:
                        bitstring = wire_type.to_bitstring(input_line[wire_name])
                    except:
                        logger.error('Error in wire: {}'.format(wire_name))
                        raise
                else:
                    bitstring = 'X' * wire_type.width
                bitstrings.append(bitstring)
            lines.append(''.join(bitstrings))
        content = '\n'.join(lines)
        f = open(filename, 'w')
        f.write(content)
        f.close()

    def read_output_file(self, filename):
        output_data = []
        with open(filename, 'r') as f:
            for line in f:
                start_pos = 0
                output_line = {}
                for wire_name, wire_type in self.wires_out:
                    end_pos = start_pos + wire_type.width
                    output_line[wire_name] = wire_type.from_bitstring(line[start_pos: end_pos])
                    start_pos = end_pos
                output_data.append(output_line)
        return output_data

    def make_inner_wrapper_params(self):
        signals_in = []
        for wire_name, wire_type in self.wires_in:
            signal = {
                'name': wire_name,
                'from_slv': wire_type.conversion_from_slv(
                    'idw_slv_' + wire_name),
                'width': wire_type.width,
                'typ': wire_type.typ(),
                'direction': 'in',
            }
            signals_in.append(signal)
        signals_out = []
        for wire_name, wire_type in self.wires_out:
            signal = {
                'name': wire_name,
                'to_slv': wire_type.conversion_to_slv(
                    'idw_' + wire_name),
                'width': wire_type.width, 
                'typ': wire_type.typ(),
                'direction': 'out',
            }
            signals_out.append(signal)
        return {
            'signals_in': signals_in,
            'signals_out': signals_out,
            'dut_name': self.module_name,
            'dut_parameters': self.module_parameters,
            'packages': self.packages,
            'clock_names': self.clock_names,
            'wrapped_module_name': self.wrapped_module_name
        }


    def make_outer_wrapper_params(self):
        # How big are the combined input and output wires
        total_width_in = sum([wire_type.width
                              for wire_name, wire_type in self.wires_in])
        total_width_out = sum([wire_type.width
                               for wire_name, wire_type in self.wires_out])

        end_index = total_width_in-1
        signals_in = []
        for wire_name, wire_type in self.wires_in:
            start_index = end_index - wire_type.width + 1
            signal = {
                'source': 'in_data({} downto {})'.format(
                    end_index, start_index),
                'name': wire_name,
                'width': wire_type.width,
            }
            end_index = start_index - 1
            signals_in.append(signal)
        signals_out = []
        for wire_name, wire_type in self.wires_out:
            signal = {
                'name': wire_name,
                'width': wire_type.width,
            }
            signals_out.append(signal)
        return {
            'total_width_in': total_width_in,
            'total_width_out': total_width_out,
            'signals_in': signals_in,
            'signals_out': signals_out,
        }

    def make_dummy_wrapper_file(self, directory):
        '''
        Makes a dummy wrapper than does absolutely nothing.
        Useful for wrapping IP blocks to test them.
        '''
        template_fn = os.path.join(config.hdldir, 'wrapper', 'dummy_wrapper.vhd.t')
        output_fn = os.path.join(directory, 'dummy_wrapper.vhd')
        params = self.make_inner_wrapper_params()
        utils.format_file(template_filename=template_fn,
                          output_filename=output_fn,
                          parameters=params)
        return output_fn

    def make_inner_wrapper_file(self, directory):
        template_fn = os.path.join(config.hdldir, 'wrapper', 'inner_wrapper.vhd.t')
        output_fn = os.path.join(directory, 'inner_wrapper.vhd')
        params = self.make_inner_wrapper_params()
        utils.format_file(template_filename=template_fn,
                          output_filename=output_fn,
                          parameters=params)
        return output_fn
        
    def make_outer_wrapper_file(self, directory):
        template_fn = os.path.join(config.hdldir, 'wrapper', 'outer_wrapper.vhd.t')
        output_fn = os.path.join(directory, 'outer_wrapper.vhd')
        params = self.make_outer_wrapper_params()
        utils.format_file(template_filename=template_fn,
                          output_filename=output_fn,
                          parameters=params)
        return output_fn

    def make_simulation_wrapper_files(self, directory):
        simulation_wrappers = [
            self.make_outer_wrapper_file(directory),
        ]
        return simulation_wrappers

    def make_design_wrapper_files(self, directory):
        design_wrappers = [
            self.make_inner_wrapper_file(directory),
        ]
        if self.needs_dummy:
            design_wrappers.append(self.make_dummy_wrapper_file(directory))
        return design_wrappers
