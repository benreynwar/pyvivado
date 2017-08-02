import os
import logging
import random

import pytest

from pyvivado import config, connection, test_utils, test_info, axi

from pyvivado.hdl.test import axi_adder

logger = logging.getLogger(__name__)


class BasicTest(test_utils.AxiTest):

    def prepare(self):
        '''
        Sends a number of 'add_numbers' commands.
        Returns a list of futures for the results and a list
        of the expected values.
        '''
        comm = axi_adder.AxiAdderComm(address_offset=0, handler=self.handler)
        n_data = 20
        max_int = pow(2, 16)-1
        self.expected_intCs = []
        self.intC_futures = []
        logger.debug('preparing data')
        for i in range(n_data):
            intA = random.randint(0, max_int)
            intB = random.randint(0, max_int)
            self.expected_intCs.append(intA + intB)
            future = comm.add_numbers(intA, intB)
            self.intC_futures.append(future)
        # Flush the communication for simulations.
        # Ignored in FPGA.
        self.handler.send([axi.FakeWaitCommand(clock_cycles=10)])

    def check(self, pause=False):
        output_intCs = [f.result() for f in self.intC_futures]
        if pause and (output_intCs != self.expected_intCs):
            import pdb
            pdb.set_trace()
        assert(output_intCs == self.expected_intCs)


@pytest.mark.parametrize('sim_type', test_info.test_sim_types)
def test_axi_adder(sim_type):
    random.seed(0)
    directory = os.path.join(config.testdir, 'test', 'proj_axi_adder')
    params = {'factory_name': 'axi_adder',
              'top_name': 'axi_adder',
              'clock_period': 10,
              }
    test_utils.axi_run_and_test(
        tests=[BasicTest()],
        params=params,
        directory=directory,
        sim_type=sim_type,
        overwrite_ok=True,
    )


@pytest.mark.skipIf(connection.get_free_hwcode(config.default_board) is None,
                    "No available hardware")
def test_axi_adder_on_fpga(self):
    test_axi_adder(sim_type='fpga')

if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_axi_adder(sim_type='fpga')
