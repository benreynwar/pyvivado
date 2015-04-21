import os
import unittest
import shutil
import logging
import time

from pyvivado import config, project

logger = logging.getLogger('pyvivado.test_project')


class TestProject(unittest.TestCase):
    
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
    config.setup_for_test()
    unittest.main()
    
        
