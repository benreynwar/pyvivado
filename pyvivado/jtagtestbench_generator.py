import logging
import os
import collections

import jinja2

logger = logging.getLogger(__name__)


def make_jtagtestbench(top_entity, generics, clk_b=False, use_reset=True):
    # Make records for inputs and outputs.
    template_fn = os.path.join(os.path.dirname(__file__), 'templates', 'jtag_testbench.vhd')
    with open(template_fn, 'r') as f:
        filetestbench_template = jinja2.Template(f.read())
    new_generics = {}
    for k, v in generics.items():
        if isinstance(v, str):
            if v[0] != "'":
                v = '"' + v + '"'
        new_generics[k] = v
    jtagtestbench = filetestbench_template.render(
        dut_name=top_entity,
        dut_parameters=new_generics,
        clk_b = clk_b,
        use_reset = use_reset,
        )
    return jtagtestbench


def prepare_files(directory, filenames, top_entity, generics, clk_b=False, use_reset=True):
    jtb = make_jtagtestbench(top_entity, generics, clk_b=clk_b, use_reset=use_reset)
    jtb_fn = os.path.join(directory, '{}_jtag.vhd'.format(top_entity))
    with open(jtb_fn, 'w') as f:
        f.write(jtb)
    new_fns = []
    new_fns.append(jtb_fn)
    return new_fns


def get_files_and_ip(directory, filenames, top_entity, generics, board_params,
                     frequency, frequency_b=None):
    clk_b = (frequency_b is not None)
    new_fns = prepare_files(directory, filenames, top_entity, generics, clk_b=clk_b,
                            use_reset=board_params['use_reset'])
    xdc_file = board_params['xdc_filename']
    clk_wiz_params = collections.OrderedDict((
        ('CLKOUT2_USED', 'true'),
        ('CLKOUT3_USED', 'false'),
        ('PRIM_IN_FREQ', board_params['clock_frequency']),
        ('PRIM_SOURCE', board_params['clock_type']),
        ('CLKOUT1_REQUESTED_OUT_FREQ', board_params['jtagtoaxi_frequency']),
        ('CLKOUT2_REQUESTED_OUT_FREQ', frequency),
        ))
    if frequency_b:
        clk_wiz_params['CLKOUT3_USED'] = 'true'
        clk_wiz_params['CLKOUT3_REQUESTED_OUT_FREQ'] = frequency_b
    ips = (
        ('clk_wiz', clk_wiz_params, 'clk_wiz_0'),
        ('jtag_axi', {
            'PROTOCOL': 2,
        }, 'jtag_axi_0'),
        ('axi_clock_converter', {
            'PROTOCOL': 'AXI4LITE',
            'DATA_WIDTH': 32,
            'ID_WIDTH': 0,
            'AWUSER_WIDTH': 0,
            'ARUSER_WIDTH': 0,
            'RUSER_WIDTH': 0,
            'WUSER_WIDTH': 0,
            'BUSER_WIDTH': 0,
        }, 'axi_clock_converter_0'),
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
    from axilent.examples import axi_adder
    work_root = '/home/ben/Code/local/deleteme_test_axi_adder'
    corename = 'axi_adder'
    entityname = 'axi_adder'
    slvcodec_config.setup_fusesoc([axilent.coresdir])

    from pyvivado import vivado_project
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
