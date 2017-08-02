import os
import logging
import shutil

from pyvivado import interface, signal, config, builder

logger = logging.getLogger(__name__)


class TestEBuilder(builder.Builder):

    test_switches = ('COPYA', 'COPYB', 'RAWA', 'RAWB')
    test_switch = 'COPYA'

    @classmethod
    def set_test_switch(cls, switch):
        if switch not in cls.test_switches:
            raise ValueError('Not a valid test switch: {}'.format(switch))
        cls.test_switch = switch

    def __init__(self, params, top_params={}):
        super().__init__(params)

    def required_filenames(self, directory):
        switch_fns = {
            'COPYA': os.path.join(directory, 'testE.vhd'),
            'COPYB': os.path.join(directory, 'testE.vhd'),
            'RAWA': os.path.join(config.hdldir, 'test', 'testEa.vhd'),
            'RAWB': os.path.join(config.hdldir, 'test', 'testEb.vhd'),
            }
        fns = [switch_fns[self.test_switch]]
        return fns

    def build(self, directory):
        dest_fn = os.path.join(directory, 'testE.vhd')
        srca_fn = os.path.join(config.hdldir, 'test', 'testEa.vhd')
        srcb_fn = os.path.join(config.hdldir, 'test', 'testEb.vhd')
        if self.test_switch == 'COPYA':
            shutil.copyfile(srca_fn, dest_fn)
        elif self.test_switch == 'COPYB':
            shutil.copyfile(srcb_fn, dest_fn)


def get_testE_interface(params):
    module_name = 'TestE'
    builder = TestEBuilder({})
    wires_in = (
        ('i', signal.std_logic_type),
    )
    wires_out = (
        ('o', signal.std_logic_type),
    )
    iface = interface.Interface(
        wires_in, wires_out, module_name=module_name,
        parameters=params, builder=builder)
    return iface

interface.add_to_module_register('TestE', get_testE_interface)
