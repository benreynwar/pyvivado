import os
import unittest
import shutil
import logging
import time

from pyvivado import config, project, redis_connection

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
            h = project.BuilderProject.predict_hash(
                design_builders=design_builders,
                simulation_builders=simulation_builders,
                parameters=parameters,
                temp_directory=temp_directory,
                directory=directory,
            )
            return h
        
        hs = []
        for i in range(10):
            h = get_hash(
                data_width=3,
                array_length=4,
                directory='blah',
                temp_directory=os.path.join(
                    config.testdir, 'test_hash_prediction_{}'.format(i)),
            )
            self.assertEqual(h, b'\x02$\xfb\x94\xd8\xe7\xd9\x10\xee\xe3\x18\x0b\x8e\x18F&a\x84\xe3\xcc')

    def test_one(self):
        logger.debug('Running TestProject.test_one')
        dn = os.path.join(config.testdir, 'proj_test_project')
        if os.path.exists(dn):
            shutil.rmtree(dn)
        os.makedirs(dn)
        p = project.Project.create(
            directory=dn,
            design_files = [os.path.join(config.hdldir, 'test', 'testA.vhd')],
            simulation_files = [os.path.join(config.hdldir, 'test', 'testA.vhd')],
        )
        t = p.get_most_recent_task()
        while not t.is_finished():
            logger.debug('Waiting for tasks to finish.')
            time.sleep(1)
        errors = t.get_errors()
        for error in errors:
            logger.error(error)
        self.assertTrue(len(errors) == 0)

if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    unittest.main()
    
        
