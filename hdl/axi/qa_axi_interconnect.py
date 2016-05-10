import os
import unittest
import logging

import testfixtures

from pyvivado import config, test_utils, axi
from pyvivado.hdl.axi import axi_interconnect

logger = logging.getLogger(__name__)


class TestAxiInterconnect(unittest.TestCase):

    def test_one(self):
        logger.debug('Starting testone')
        test_name = 'test_axi_interconnect'
        sim_type = 'vivado_hdl'
        pause = False

        directory = os.path.join(
            config.testdir, 'axi', 'proj_qa_axi_interconnect')

        slave_ids = (13, 15, pow(2, 16)-7)
        invalid_slave_id = 14

        interface = axi_interconnect.get_axi_interconnect_interface(
            params={'slave_ids': slave_ids})

        wait_data = []
        wait_lines = 20
        input_data = []
        expected_data = []

        make_m2s = axi.make_empty_axi4lite_m2s_dict
        make_s2m = axi.make_empty_axi4lite_s2m_dict

        for i in range(wait_lines):
            wait_data.append({
                'reset': 1,
                'i_m': make_m2s(),
                'i_s': [make_s2m() for i in slave_ids],
            })


        # Now write to an invalid address.
        invalid_write_d = make_m2s()
        local_address = 18
        write_data = 3456
        invalid_write_d['awaddr'] = invalid_slave_id * pow(2, 16) + local_address
        invalid_write_d['awvalid'] = 1
        invalid_write_d['wvalid'] = 1
        invalid_write_d['wdata'] = write_data
        input_data.append({
            'reset': 0,
            'i_m': invalid_write_d,
            'i_s': [make_s2m() for slave_id in slave_ids],
        })
        input_data.append({
            'reset': 0,
            'i_m': make_m2s(),
            'i_s': [make_s2m() for slave_id in slave_ids],
        })
        e_m2s = make_m2s()
        e_m2s['awaddr'] = local_address
        e_m2s['wdata'] = write_data
        expected_data.append({
            'o_m': make_s2m(),
            'o_s': [e_m2s] * len(slave_ids),
        })
        e_s2m = make_s2m()
        e_s2m['bresp'] = axi.DECERR
        e_s2m['bvalid'] = 1
        expected_data.append({
            'o_m': e_s2m,
            'o_s': [make_m2s() for i in slave_ids],
        })
        # Now write to a valid address.
        valid_write_d = make_m2s()
        local_address = 490
        write_data = 4567
        valid_write_d['awaddr'] = slave_ids[1] * pow(2, 16) + local_address
        valid_write_d['awvalid'] = 1
        valid_write_d['wvalid'] = 1
        valid_write_d['wdata'] = write_data
        input_data.append({
            'reset': 0,
            'i_m': valid_write_d,
            'i_s': [make_s2m() for slave_id in slave_ids],
        })
        d_s2m = make_s2m()
        d_s2m['bvalid'] = 1
        bresp = 2
        d_s2m['bresp'] = bresp
        input_data.append({
            'reset': 0,
            'i_m': make_m2s(),
            'i_s': [make_s2m(), d_s2m, make_s2m()],
        })
        e_m2s_valid = make_m2s()
        e_m2s_valid['awaddr'] = local_address
        e_m2s_valid['awvalid'] = 1
        e_m2s_valid['wdata'] = write_data
        e_m2s_valid['wvalid'] = 1
        e_m2s_invalid = make_m2s()
        e_m2s_invalid['awaddr'] = local_address
        e_m2s_invalid['wdata'] = write_data
        expected_data.append({
            'o_m': make_s2m(),
            'o_s': [e_m2s_invalid, e_m2s_valid, e_m2s_invalid],
        })
        e_s2m = make_s2m()
        e_s2m['bresp'] = bresp
        e_s2m['bvalid'] = 1
        expected_data.append({
            'o_m': e_s2m,
            'o_s': [make_m2s() for i in slave_ids],
        })
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
    unittest.main()
