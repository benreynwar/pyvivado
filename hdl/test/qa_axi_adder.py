import os
import unittest
import shutil
import logging
import random
import math
import time

import testfixtures

from pyvivado import project, axi, config, connection
from pyvivado.hdl.test import axi_adder

logger = logging.getLogger(__name__)

class TestAxiAdder(unittest.TestCase):

    def send_commands(self, handler):
        '''
        Sends a number of 'add_numbers' commands.
        Returns a list of futures for the results and a list
        of the expected values.
        '''
        comm = axi_adder.AxiAdderComm(address_offset=0, handler=handler)
        n_data = 20
        max_int = pow(2, 16)-1
        expected_intCs = []
        intC_futures = []
        for i in range(n_data):
            intA = random.randint(0, max_int)
            intB = random.randint(0, max_int)
            expected_intCs.append(intA + intB)
            intC_futures.append(comm.add_numbers(intA, intB))
        return intC_futures, expected_intCs

    def test_with_hdl_simulation(self):
        random.seed(0)

        directory = os.path.abspath('proj_testaxiadder')
        interface = axi_adder.get_axi_adder_interface({})

        # Create input data for the sending of a reset signal.
        wait_data = []
        wait_lines = 20
        for wait_index in range(wait_lines):
            wait_data.append({
                'reset': 1,
                'i': axi.make_empty_axi4lite_m2s_dict(),
            })

        # Create input data for the setting and reading of the 
        # registers (all the heavy work is done above in send_commands)
        handler = axi.DictCommandHandler()
        future_intCs, expected_intCs = self.send_commands(handler)
        input_data = []
        for d in handler.make_command_dicts():
            input_data.append({
                'reset': 0,
                'i': d,
            })
        
        # Create the project and run the simulation
        p = project.FileTestBenchProject.create_or_update(
            interface=interface, directory=directory,
            board=config.default_board,
            part=config.default_part,
        )
        errors, output_data = p.run_simulation(input_data=wait_data+input_data)
        # Process the output axi connection.
        response_dicts = [d['o'] for d in output_data]
        handler.consume_response_dicts(response_dicts) 

        # Now that the simulation has been run and the output processed
        # our futures should be populated.
        output_intCs = [f.result() for f in future_intCs]
        self.assertEqual(output_intCs, expected_intCs)

    @unittest.skipIf(connection.get_free_hwcode() is None,
                     "No available hardware")
    def test_on_fpga(self):
        random.seed(1)
        directory = os.path.abspath('proj_testaxiadderfpga')
        the_builder = axi_adder.AxiAdderBuilder({})
        connection.kill_free_monitors(directory)
        # Create the project, synthesize, implement and deploy to the FPGA.
        p = project.FPGAProject.create_or_update(
            the_builder=the_builder,
            parameters={
                # The name of the top module.
                'top_name': 'axi_adder',
                # The name of the generator of this module.
                # i.e. For looking up the builder, interface or comm.
                'factory_name': 'axi_adder',
                # The frequency to run the module at on the FPGA.
                'frequency': 100,
            },
            directory=directory,
            board=config.default_board,
            part=config.default_part,
        )
        t = p.implement()
        t.wait()
        errors = t.get_errors()
        self.assertEqual(len(errors), 0)
        # Send this project's bistream to an FPGA and launch a Vivado
        # process to monitor it.
        t, conn = p.send_to_fpga_and_monitor()
        # Send commands to the FPGA
        handler = axi.ConnCommandHandler(conn)
        future_intCs, expected_intCs = self.send_commands(handler)
        # And kill the monitor
        conn.kill_monitor()
        # Futures are immediately resolved by ConnCommandHandler
        # so we can check if they are correct.
        output_intCs = [f.result() for f in future_intCs]
        self.assertEqual(output_intCs, expected_intCs)

if __name__ == '__main__':
    config.setup_logging(logging.WARNING)
    unittest.main()

