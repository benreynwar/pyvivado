import os
import logging

from pyvivado import interface, signal, config, builder

logger = logging.getLogger(__name__)


def get_data_type(data_width):
    return signal.StdLogicVector(width=data_width, name='t_data')


class TestCBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.width = params['width']
        self.module_name = 'TestC'

    def built_filename(self, directory):
        return os.path.join(directory, 'TestC.v')

    def required_filenames(self, directory):
        return [self.built_filename(directory)]

    def build(self, directory):
        command = 'run TestC {} --dataWidth {}'.format(
            directory, self.width)
        builder.run_sbt_command(config.basedir, command)


def get_testC_interface(params):
    module_name = 'TestC'
    width = params['width']
    builder = TestCBuilder({'width': width})
    wires_in = (
        ('io_i_valid', signal.std_logic_type),
        ('io_i_data', signal.StdLogicVector(width=width)),
    )
    wires_out = (
        ('io_o_valid', signal.std_logic_type),
        ('io_o_data', signal.StdLogicVector(width=width)),
    )
    iface = interface.Interface(
        wires_in, wires_out, module_name=module_name,
        builder=builder, parameters=params)
    return iface

name = 'TestC'
interface.add_to_module_register(name,  get_testC_interface)
