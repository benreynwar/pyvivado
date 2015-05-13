import os
import logging

from pyvivado import interface, signal, config, builder

logger = logging.getLogger(__name__)

TestBBuilder = builder.make_simple_builder(filenames=[
    os.path.join(config.hdldir, 'test', 'testB.sv')])
    
def get_testB_interface(params):
    module_name = 'TestB'
    data_width = params['data_width']
    builder = TestBBuilder({})
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
        builder=builder, language='systemverilog')
    return iface

name = 'TestB'
interface.add_to_module_register(name,  get_testB_interface)
