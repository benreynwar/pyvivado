import os
import unittest
import random
import logging

import pytest
import testfixtures

from pyvivado import signal, config, test_utils

from pyvivado.hdl.tree import tree

# Required to import modules into registry
from pyvivado.hdl.tree import tree_maximum, tree_minimum


logger = logging.getLogger(__name__)


class TestTree(unittest.TestCase):

    def default_test(self):
        test_tree(tree_name='maximum', n_inputs=3, width=4)

compare_functions = (
    ('minimum', lambda x, y: x < y),
    ('maximum', lambda x, y: x > y)
)

combinations = []
msg_width = 11
for tree_name, compare_function in compare_functions:
    for n_inputs in range(1, 17):
        combinations.append((tree_name, n_inputs, msg_width))

@pytest.mark.parametrize('tree_name,n_inputs,width', combinations)
def test_tree(tree_name, n_inputs, width):

    directory = os.path.join(
        config.testdir, 'tree', 'proj_tree_{}_{}_{}'.format(tree_name, n_inputs, width))
    test_name = 'test_tree'

    n_data = 100
    data = []
    maxvalue = pow(2, width)-1
    for i in range(n_data):
        values = [random.randint(0, maxvalue) for j in range(n_inputs)]
        data.append(values)

    # Make wait data.  Sent while initialising.
    n_wait_lines = 20
    wait_data = []
    for wait_index in range(n_wait_lines):
        wait_data.append({
            'i_data': 0,
        })

    # Make input and expected data
    input_data = []
    expected_data = []
    expected_indices = []
    for values in data:
        input_data.append({
            'i_data': signal.list_of_uints_to_uint(values, width=width),
        })
        minval = None
        for i, v in enumerate(values):
            compare_function = dict(compare_functions)[tree_name]
            if ((minval is None) or 
                compare_function(v, minval)):
                minval = v
                minindex = i
        expected_data.append(minval)
        expected_indices.append(minindex)
    input_data.append({
        'i_data': 0,
    })

    interface = tree.get_tree_interface({
        'width': width,
        'n_inputs': n_inputs,
        'tree_name': tree_name,
        'module_name': 'tree_{}'.format(tree_name),
        'builder_name': 'tree_{}'.format(tree_name),
    })

    output_data = test_utils.simulate(
        interface=interface, directory=directory,
        data=wait_data+input_data,
        test_name=test_name,
    )[n_wait_lines: n_wait_lines+n_data]
    assert(len(expected_data) == n_data)
    assert(len(expected_indices) == n_data)
    o_data = [d['o_data'] for d in output_data]
    o_address = [d['o_address'] for d in output_data]
    testfixtures.compare(expected_data, o_data)
    testfixtures.compare(expected_indices, o_address)

if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_utils.run_test(TestTree)
