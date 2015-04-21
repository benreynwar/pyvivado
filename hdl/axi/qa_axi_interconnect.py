import os
import unittest
import shutil
import logging

import testfixtures

from pyvivado import project, signal, config
from pyvivado.hdl.axi import axi_interconnect, axi_utils

logger = logging.getLogger(__name__)

class TestAxiInterconnect(unittest.TestCase):

    def test_one(self):
        logger.debug('Starting testone')

        directory = os.path.abspath('proj_qa_axi_interconnect')
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.mkdir(directory)

        slave_ids = (13, 15, pow(2, 16)-7)
        invalid_slave_id = 14

        interface = axi_interconnect.get_axi_interconnect_interface(
            params={'slave_ids': slave_ids})

        wait_data = []
        wait_lines = 20
        input_data = []
        expected_data = []

        make_m2s = axi_utils.make_empty_axi4lite_m2s_dict
        make_s2m = axi_utils.make_empty_axi4lite_s2m_dict

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
        e_s2m['bresp'] = axi_utils.DECERR
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

        p = project.FileTestBenchProject.create(
            interface=interface, directory=directory,
            board=config.default_board,
            part=config.default_part,
        )

        t = p.wait_for_most_recent_task()
        errors = t.get_errors_and_warnings()
        logger.debug('errors are {}'.format(errors))
        self.assertEqual(len(errors), 0)

        # Run the simulation
        runtime = '{} ns'.format((len(wait_data+input_data) + 20) * 10)
        errors, output_data = p.run_hdl_simulation(
            input_data=wait_data+input_data, runtime=runtime)
        
        self.assertEqual(len(errors), 0)

        latency = 0
        delay = wait_lines + latency + 1

        import pdb
        pdb.set_trace()
        for data in (output_data, expected_data):
            for d in data:
                pass
        self.check_output(output_data[delay:], expected_data)

    def check_output(self, output_data, expected_data):
        self.assertTrue(len(output_data) >= len(expected_data))
        output_data = output_data[:len(expected_data)]
        testfixtures.compare(output_data, expected_data)


if __name__ == '__main__':
    config.use_test_db()
    config.setup_logging(logging.DEBUG)
    unittest.main()

