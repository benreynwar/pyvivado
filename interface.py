import os
import logging
import collections

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
        self.module_parameters = collections.OrderedDict(
            sorted(list(module_parameters.items())))
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

