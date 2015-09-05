import os
import logging

from pyvivado import interface, signal, builder, config

from pyvivado.hdl.tree import tree

logger = logging.getLogger(__name__)

class TreeBinaryLeafMaximumBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.simple_filenames = [
            os.path.join(
                config.hdldir, 'tree', 'tree_binary_leaf_maximum.vhd')
        ]


class TreeMaximumBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.builders = [
            tree.TreeBuilder({
                'tree_name': 'maximum',
                'n_inputs': params['n_inputs'],
                'width': params['width'],
                'leaf_name': 'tree_binary_leaf_maximum',
            })
        ]
            

def get_tree_maximum_interface(params):
    updated_params = params.copy()
    updated_params['builder_name'] = 'tree_maximum'
    updated_params['tree_name'] = 'maximum'
    return tree.get_tree_interface(updated_params)

name = 'tree_maximum'
assert(name not in interface.module_register)
interface.module_register[name] = get_tree_maximum_interface
assert(name not in builder.module_register)
builder.module_register[name] = TreeMaximumBuilder
name = 'tree_binary_leaf_maximum'
assert(name not in builder.module_register)
builder.module_register[name] = TreeBinaryLeafMaximumBuilder
