import os
import logging

from pyvivado import interface, signal, config, builder

logger = logging.getLogger(__name__)

factory_name = 'SimpleModule'

class SimpleModuleBuilder(builder.Builder):
    '''
    Responsible for creating (or specifying) the necessary HDL files
    and knowing with IP is required.

    Since this is a very simple module all the builder does is specify the
    VHDL file that is used.
    '''
    
    def __init__(self, params):
        super().__init__(params)
        self.simple_filenames = [
            os.path.join(config.hdldir, 'test', 'simple_module.vhd'),
        ]
        
def get_simple_module_interface(params):
    '''
    Creates an interface object that is used to generate the verification
    wrappers.
    '''
    module_name = factory_name
    data_width = params['data_width']
    builder = SimpleModuleBuilder({})
    module_parameters = {
        'DATA_WIDTH': data_width,
    }
    wires_in = (
        ('i_valid', signal.std_logic_type),
        ('i_data', signal.StdLogicVector(width=data_width)),
    )
    wires_out = (
        ('o_valid', signal.std_logic_type),
        ('o_data', signal.StdLogicVector(width=data_width)),
    )
    iface = interface.Interface(
        wires_in, wires_out, module_name=module_name,
        parameters=params, module_parameters=module_parameters,
        builder=builder)
    return iface

interface.add_to_module_register(factory_name,  get_simple_module_interface)
