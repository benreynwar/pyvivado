import os
import shutil
import logging

import testfixtures
import pytest

from pyvivado import config, axi, test_utils, test_info
from pyvivado.hdl.axi import axi_merge

logger = logging.getLogger(__name__)


class TestAxiMerge(test_utils.TestCase):

    def default_test(self):
        test_axi_merge(
            n_masters=7,
            sim_type='vivado_hdl',
            pause=False,
        )


combinations = []
for n_masters in (1, 2, 7):
    for sim_type in test_info.test_sim_types:
        combinations.append((n_masters, sim_type))

@pytest.mark.parametrize('n_masters,sim_type', combinations)
def test_axi_merge(n_masters, sim_type, pause=False):
    test_name = 'test_axi_merge'

    directory = os.path.join(config.testdir, 'axi', 'proj_axi_merge')
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.mkdir(directory)

    interface = axi_merge.get_axi_merge_interface(
        {'n_masters': n_masters})

    wait_data = []
    wait_lines = 20
    input_data = []
    expected_data = []

    make_m2s = axi.make_empty_axi4lite_m2s_dict
    make_s2m = axi.make_empty_axi4lite_s2m_dict

    for i in range(wait_lines):
        wait_data.append({
            'reset': 1,
            'i_s': make_s2m(),
            'i_m': [make_m2s() for i in range(n_masters)],
        })
    # Now write to an invalid address.
    # Write to slave from master 0
    write_m2s = make_m2s()
    write_m2s['awvalid'] = 1
    write_m2s['wvalid'] = 1
    write_m2s['awaddr'] = 2
    write_m2s['wdata'] = 27
    input_data.append({
        'reset': 0,
        'i_s': make_s2m(),
        'i_m': [write_m2s] + [make_m2s() for n in range(n_masters-1)],
    })
    response_s2m = make_s2m()
    response_s2m['bvalid'] = 1
    input_data.append({
        'reset': 0,
        'i_s': response_s2m,
        'i_m': [make_m2s() for n in range(n_masters)],
    })
    # Master 1 reads from slave.
    write_m2s = make_m2s()
    write_m2s['arvalid'] = 1
    write_m2s['araddr'] = 3
    input_data.append({
        'reset': 0,
        'i_s': make_s2m(),
        'i_m': [write_m2s] + [make_m2s() for n in range(n_masters-1)],
    })
    response_s2m = make_s2m()
    response_s2m['rvalid'] = 1
    response_s2m['rdata'] = 16
    input_data.append({
        'reset': 0,
        'i_s': response_s2m,
        'i_m': [make_m2s() for n in range(n_masters)],
    })
    # Extra blank input so it moves to look at master 2
    input_data.append({
        'reset': 0,
        'i_s': make_s2m(),
        'i_m': [make_m2s() for n in range(n_masters)],
    })
    # Write to slave from master 2 again.
    write_m2s = make_m2s()
    write_m2s['awvalid'] = 1
    write_m2s['wvalid'] = 1
    write_m2s['awaddr'] = 3
    write_m2s['wdata'] = 28
    input_data.append({
        'reset': 0,
        'i_s': make_s2m(),
        'i_m': [make_m2s() for n in range(n_masters-1)] + [write_m2s],
    })
    response_s2m = make_s2m()
    response_s2m['bvalid'] = 1
    input_data.append({
        'reset': 0,
        'i_s': response_s2m,
        'i_m': [make_m2s() for n in range(n_masters)],
    })

    py = axi_merge.AxiMerge(n_masters)
    for d in wait_data:
        py.process(d)
    for d in input_data:
        expected_data.append(py.process(d))

    output_data = test_utils.simulate(
        test_name=test_name,
        interface=interface, directory=directory,
        data=wait_data+input_data,
        sim_type=sim_type,
    )[wait_lines:]
    if pause:
        import pdb
        pdb.set_trace()
    assert(len(output_data) >= len(expected_data))
    output_data = output_data[:len(expected_data)]
    testfixtures.compare(output_data, expected_data)


if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_utils.run_test(TestAxiMerge)
