import os
import logging
import math
import random

from pyvivado import interface, signal, builder, utils, config, axi

from pyvivado.hdl.axi import axi_utils

logger = logging.getLogger(__name__)
class AxiAdderBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.module_name = 'axi_adder'
        self.simple_filenames = [
            os.path.join(config.hdldir, 'test', 'axi_adder.vhd'),
        ]
        self.packages = [
            'axi_utils',
        ]

def get_axi_adder_interface(params):
    module_name = 'axi_adder'
    builder = AxiAdderBuilder({})
    wires_in = (
        ('reset', signal.std_logic_type),
        ('i', axi.axi4lite_m2s_type),
    )
    wires_out = (
        ('o', axi.axi4lite_s2m_type),
    )
    packages = [
        'work.axi_utils',
    ]
    iface = interface.Interface(
        wires_in, wires_out, module_name=module_name,
        packages=packages,
        parameters=params, builder=builder, clock_names=['clk'],
    )
    return iface


class AxiAdderComm(axi.Comm):

    INTA_ADDRESS = 0
    INTB_ADDRESS = 1
    INTC_ADDRESS = 2
    HAD_ERROR_ADDRESS = 3
    
    def __init__(self, address_offset, handler):
        '''
        `address_offset` is any addition that is made to the address that is
        consumed during routing.
        `handler` is the object responsible for dispatching the commands.
        '''
        self.handler = handler
        self.address_offset = address_offset
        self.addresses = {
            'intA': address_offset + self.INTA_ADDRESS,
            'intB': address_offset + self.INTB_ADDRESS,
            'intC': address_offset + self.INTC_ADDRESS,
            'had_error': address_offset + self.HAD_ERROR_ADDRESS,
        }

    def had_error(self):
        '''
        A simple command accessing an address over AXI.
        '''
        self.get_boolean(self.addresses['had_error'])

    def add_numbers(self, a, b):
        '''
        A complex complex command that write to two registers and
        then reads from another.
        Sets 'a' and 'b' then reads 'c' (should be a+b)
        '''
        command = AddNumbersCommand(a, b, self.addresses)
        self.handler.send([command])
        return command.future


class AddNumbersCommand(axi.CommCommand):
    '''
    A command that writes to the intA and intB registers
    and then reads from the intC register.
    The effect is the add the two inputs.
    '''
    
    def __init__(self, a, b, addresses):
        super().__init__()
        write_a_commands = self.set_unsigned_commands(
            address=addresses['intA'], value=a)
        write_b_commands = self.set_unsigned_commands(
            address=addresses['intB'], value=b)
        read_c_commands = self.get_unsigned_commands(
            address=addresses['intC'])
        self.axi_commands = (
            write_a_commands + write_b_commands + read_c_commands)

    def process_result(self, result):
        '''
        Return the third response (from the final read command)
        Don't return any errors.
        '''
        c = result[2][0]
        return None, c

name = 'axi_adder'
interface.add_to_module_register(name, get_axi_adder_interface)
