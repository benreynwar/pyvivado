import os
import unittest
import shutil
import logging

import testfixtures

from pyvivado import project, signal, config, axi
from pyvivado.hdl.axi import axi_merge

logger = logging.getLogger(__name__)

class TestAxiMerge(unittest.TestCase):

    def test_one(self):
        logger.debug('Starting testone')

        directory = os.path.abspath('proj_qa_axi_merge')
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.mkdir(directory)

        n_masters = 2

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
        import pdb
        pdb.set_trace()

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
        errors, output_data = p.run_simulation(
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

