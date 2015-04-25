import os
import logging
import collections

from pyvivado import utils, config

logger = logging.getLogger(__name__)

# Functions to generate interfaces are registered here by the module name.
module_register = {}

def add_to_module_register(name, get_interface_fn):
    '''
    Add a function to generate interfaces to the register.
    '''
    if name in module_register:
        logger.warning('{} placed in module register twice (If this happens during testing probably OK because modules are sometimes imported twice.'.format(name))
    module_register[name] = get_interface_fn


class Interface(object): 
    '''
    An interface contains all the information necessary to generate the wrappers
    required for validation projects.
    '''
    
    def __init__(self, wires_in, wires_out, module_name, parameters,
                 builder, module_parameters={}, packages=[],
                 clock_names=[], factory_name=None,
                 needs_dummy=False, constants=[]):
        '''
        wires_in: A list of tuples of (wire_name, wire_type) where wire type is
            a `SignalType` object.  Represents the inputs to module.
        wires_out: A list of tuples of (wire_name, wire_type) where wire type is
            a `SignalType` object.  Represents the outputs from module.
        module_name: The name of the module.
        parameters: Parameters necessary to work out the signal types (not the
            generic parameters of the module itself).
        builder: A `Builder` that generates and specifies the files and IP required
            by the module.
        module_parameters: The generic parameters to specify for the module.
        packages: A list of packages that are required by a wrapper around the module.
            (i.e. The packages that define the input and output types).
        clock_names: A list of input clocks for the module.
        factory_name: The IP blocks the factory_name is the name of the IP block. The
            module_name may be different since it is specific to that set of IP
            parameters.
        needs_dummy: Generates an extra wrapper around the module that does nothing.
            Necessary when creating interfaces to simulate a IP block by itself.
        constants: Somewhere to throw other values that you want to store in the
            interface.
        '''
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
        self.needs_dummy = needs_dummy
        self.wrapped_module_name = self.module_name
        self.constants = constants
        if needs_dummy:
            self.module_name = 'DummyDutWrapper'

    def total_width_in(self):
        '''
        Get the total width of all the input wires.
        '''
        width = 0
        for wire_name, wire_type in self.wires_in:
            width += wire_type.width
        return width

    def total_width_out(self):
        '''
        Get the total width of all the output wires.
        '''
        width = 0
        for wire_name, wire_type in self.wires_out:
            width+= wire_type.width
        return width

    def write_input_file(self, input_data, filename):
        '''
        Write a text file to use as input for a simulation.
        `input_data`: A list of dictionaries of values for the input wires.
        `filename`: Where the file is written.
        '''
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
        '''
        Read the output file from a simulation and parse it to a list
        of dictionaries of the values in the output wires.

        `filename`: The filename to parse.
        '''
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

