import os
import logging

from pyvivado import interface, signal, config, info, builder

logger = logging.getLogger(__name__)

def get_data_type(data_width):
    return signal.StdLogicVector(width=data_width, name='t_data')


class TestADefinitionsBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.data_width = params['data_width']

    def get_filename(self, directory):
        return os.path.join(directory, 'testA_definitions.vhd')

    def build(self, directory):
        package_name = 'testA_definitions'
        data_type = get_data_type(self.data_width)
        signal.make_defs_file(
            self.get_filename(directory), package_name,
            [data_type], [data_type])
        
    def required_filenames(self, directory):
        return [
            self.get_filename(directory),
        ]


class TestABuilder(builder.Builder):
    
    def __init__(self, params):
        super().__init__(params)
        self.simple_filenames = [
            os.path.join(config.hdldir, 'test', 'testA.vhd'),
        ]
        self.builders = [
            TestADefinitionsBuilder(params),
        ]

        
def get_testA_interface(params):
    module_name = 'TestA'
    data_width = params['data_width']
    array_length = params['array_length']
    builder = TestABuilder({'data_width': data_width})
    packages = ['work.testA_definitions']
    data_type = get_data_type(data_width)    
    array_type = signal.Array(contained_type=data_type, size=array_length)
    module_parameters = {
        'DATA_WIDTH': data_width,
        'ARRAY_LENGTH': array_length,
    }
    wires_in = (
        ('i_valid', signal.std_logic_type),
        ('i_data', data_type),
        ('i_array', array_type)
    )
    wires_out = (
        ('o_valid', signal.std_logic_type),
        ('o_data', data_type),
        ('o_array', array_type)
    )
    iface = interface.Interface(
        wires_in, wires_out, module_name=module_name,
        parameters=params, module_parameters=module_parameters,
        packages=packages, builder=builder)
    return iface

name = 'TestA'
interface.add_to_module_register(name,  get_testA_interface)
