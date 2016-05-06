import os
import unittest
import shutil
import logging
import time

from pyvivado import config, base_project, vivado_project

from pyvivado.hdl.test import testA
from pyvivado.hdl.wrapper import inner_wrapper, file_testbench

logger = logging.getLogger('pyvivado.test_project')


class TestProject(unittest.TestCase):

    def test_hash_prediction(self):

        def get_hash(data_width, array_length, directory, temp_directory):
            interface = testA.get_testA_interface({
                'data_width': data_width,
                'array_length': array_length,
            })
            inner_wrapper_builder = inner_wrapper.InnerWrapperBuilder({
                'interface': interface,
            })
            file_testbench_builder = file_testbench.FileTestbenchBuilder({
                'interface': interface,
            })
            design_builders = [inner_wrapper_builder, interface.builder]
            simulation_builders = [file_testbench_builder]
            parameters = interface.parameters
            h = base_project.get_hash_from_builders(
                design_builders=design_builders,
                simulation_builders=simulation_builders,
                parameters=parameters,
                temp_directory=temp_directory,
                directory=directory,
                top_module='TestA',
            )
            return h

        first_hash = None
        for i in range(10):
            h = get_hash(
                data_width=3,
                array_length=4,
                directory='blah',
                temp_directory=os.path.join(
                    config.testdir, 'test_hash_prediction_{}'.format(i)),
            )
            if first_hash is None:
                first_hash = h
            else:
                assert(h == first_hash)

    def test_one(self):
        logger.debug('Running TestProject.test_one')
        dn = os.path.join(config.testdir, 'proj_test_project')
        if os.path.exists(dn):
            shutil.rmtree(dn)
        os.makedirs(dn)
        p = base_project.BaseProject(
            directory=dn,
            files_and_ip={
                'design_files': [os.path.join(config.hdldir, 'test', 'testA.vhd')],
                'simulation_files': [os.path.join(config.hdldir, 'test', 'testA.vhd')],
                'ips': [],
                'top_module': 'TestA',
                }
        )
        v = vivado_project.VivadoProject(p)
        t = v.tasks_collection.get_most_recent_task()
        t.wait(raise_errors=False)
        errors = t.get_errors()
        self.assertTrue(len(errors) == 0)

if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    unittest.main()
