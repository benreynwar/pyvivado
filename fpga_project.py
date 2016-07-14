import os
import logging

from pyvivado import boards
from pyvivado.base_project import BuilderProject
from pyvivado.hdl.wrapper import jtag_axi_wrapper

logger = logging.getLogger(__name__)


class FPGAProject(BuilderProject):
    '''
    A python wrapper around a Vivado project that is designed to be deployed
    to the FPGA and communicated with over JTAG and the JTAG-to-AXI block.
    '''

    def __init__(self, directory, the_builder=None, parameters=None, board=None,
            overwrite_ok=True):
        if parameters is None:
            design_builders = None
            simulation_builders = None
        else:    
            assert(the_builder is not None)
            assert(board is not None)
            parameters['board_params'] = boards.get_board_params(board)
            if parameters['board_params']['name'] == 'profpga:uno2000':
                jtagaxi_builder = jtag_axi_wrapper_no_reset.JtagAxiWrapperNoResetBuilder(parameters)
                top_module = 'JtagAxiWrapperNoReset'
            else:
                jtagaxi_builder = jtag_axi_wrapper.JtagAxiWrapperBuilder(parameters)
                top_module = 'JtagAxiWrapper'
            design_builders = [the_builder, jtagaxi_builder]
            simulation_builders = []
        super().__init__(
                directory=directory,
                design_builders=design_builders,
                simulation_builders=simulation_builders,
                parameters=parameters,
                overwrite_ok=overwrite_ok,
                top_module=top_module,
                )

