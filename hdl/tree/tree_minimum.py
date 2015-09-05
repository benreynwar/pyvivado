import os
import logging

from pyvivado import interface, signal, builder, config

from pyvivado.hdl.tree import tree

logger = logging.getLogger(__name__)

class TreeBinaryLeafMinimumBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.simple_filenames = [
            os.path.join(
                config.hdldir, 'tree', 'tree_binary_leaf_minimum.vhd')
        ]


class TreeMinimumBuilder(builder.Builder):

    def __init__(self, params):
        super().__init__(params)
        self.builders = [
            tree.TreeBuilder({
                'tree_name': 'minimum',
                'n_inputs': params['n_inputs'],
                'width': params['width'],
                'leaf_name': 'tree_binary_leaf_minimum',
            })
        ]
            

def get_tree_minimum_interface(params):
    updated_params = params.copy()
    updated_params['builder_name'] = 'tree_minimum'
    updated_params['tree_name'] = 'minimum'
    return tree.get_tree_interface(updated_params)

name = 'tree_minimum'
assert(name not in interface.module_register)
interface.module_register[name] = get_tree_minimum_interface
assert(name not in builder.module_register)
builder.module_register[name] = TreeMinimumBuilder
name = 'tree_binary_leaf_minimum'
assert(name not in builder.module_register)
builder.module_register[name] = TreeBinaryLeafMinimumBuilder
