import logging
import os
import time

import jinja2

from axilent import handlers
from axilent.examples import axi_adder
from pyvivado import vivado_project

logger = logging.getLogger(__name__)


def make_jtagtestbench(top_entity, generics):
    # Make records for inputs and outputs.
    template_fn = os.path.join(os.path.dirname(__file__), 'templates', 'jtag_testbench.vhd')
    with open(template_fn, 'r') as f:
        filetestbench_template = jinja2.Template(f.read())
    jtagtestbench = filetestbench_template.render(
        dut_name=top_entity,
        dut_generics=generics,
        )
    return jtagtestbench


def prepare_files(directory, filenames, top_entity, generics):
    jtb = make_jtagtestbench(top_entity, generics)
    jtb_fn = os.path.join(directory, '{}_jtag.vhd'.format(top_entity))
    with open(jtb_fn, 'w') as f:
        f.write(jtb)
    new_fns = []
    new_fns.append(jtb_fn)
    return new_fns


def get_files_and_ip(directory, filenames, top_entity, generics, board_params,
                     frequency):
    new_fns = prepare_files(directory, filenames, top_entity, generics)
    xdc_file = board_params['xdc_filename']
    ips = (
        ('clk_wiz', {
            'PRIM_IN_FREQ': board_params['clock_frequency'],
            'PRIM_SOURCE': board_params['clock_type'],
            'CLKOUT1_REQUESTED_OUT_FREQ': frequency,
        }, 'clk_wiz_0'),
        ('jtag_axi', {
            'PROTOCOL': 2,
        }, 'jtag_axi_0'),
        )
    files_and_ip = {
        'design_files': new_fns + filenames + [xdc_file],
        'simulation_files': [],
        'ips': ips,
        'top_module': top_entity + '_jtag'
        }
    return files_and_ip


if __name__ == '__main__':
    from slvcodec import config as slvcodec_config
    import axilent
    work_root = '/home/ben/Code/local/deleteme_test_axi_adder'
    corename = 'axi_adder'
    entityname = 'axi_adder'
    slvcodec_config.setup_fusesoc([axilent.coresdir])

    p = vivado_project.VivadoProject.from_fusesoc_core(
        directory=work_root,
        corename=corename,
        entityname=entityname,
        generics={},
        top_params={},
        boardname='xilinx:vc709',
        frequency=100,
        overwrite_ok=True,
    )
    tests = [axi_adder.AxiAdderTest()]
    p.implement_deploy_and_run_tests(tests)
