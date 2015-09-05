import os
import logging

from pyvivado import interface, signal, builder, config, utils

logger = logging.getLogger(__name__)

class TreeBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.tree_name = params['tree_name']
        leaf_name = params['leaf_name']
        leaf_params = params.get('leaf_params', {})
        self.packages = [
            'pyvivado_utils',
        ]
        if leaf_name:
            self.builders = [
                builder.module_register[leaf_name](leaf_params)
            ]
        self.parts = (
            'tree',
            'tree_generic',
            'tree_poweroftwo',
            'tree_notpoweroftwo',
        )
            
    def build(self, directory):
        for base_name in self.parts:
            template_fn = os.path.join(
                config.hdldir, 'tree', '{}.vhd.t'.format(base_name))
            output_fn = os.path.join(
                directory, '{}_{}.vhd'.format(base_name, self.tree_name))
            utils.format_file(template_fn, output_fn, {'tree_name': self.tree_name})
            
    def required_filenames(self, directory):
        fns = [os.path.join(
            directory, '{}_{}.vhd'.format(base_name, self.tree_name))
               for base_name in self.parts]
        return fns
            

def get_tree_interface(params):
    tree_name = params['tree_name']
    width = params['width']
    n_inputs = params['n_inputs']
    module_name = 'tree_{}'.format(tree_name)
    builder_name = params.get('builder_name', None)
    module_parameters = {
        'N_INPUTS': n_inputs,
        'WIDTH': width,
    }
    if builder_name is None:
        build = TreeBuilder(params)
    else:
        build = builder.module_register[builder_name](params)
    wires_in = (
        ('i_data', signal.StdLogicVector(width=n_inputs*width)),
    )
    wires_out = (
        ('o_data', signal.StdLogicVector(width=width)),
        ('o_address', signal.StdLogicVector(width=signal.logceil(n_inputs))),
    )
    iface = interface.Interface(
        wires_in, wires_out, module_name=module_name,
        parameters=params, builder=build, module_parameters=module_parameters,
    )
    return iface


name = 'tree'
assert(name not in interface.module_register)
interface.module_register[name] = get_tree_interface
