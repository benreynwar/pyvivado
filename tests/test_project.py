import os
import unittest
import shutil
import logging

from pyvivado import config, base_project, vivado_project

logger = logging.getLogger('pyvivado.test_project')

dir_path = os.path.dirname(os.path.realpath(__file__))
output_dir = os.path.join(dir_path, '..', 'test_outputs')
if not os.path.exists(output_dir):
    os.mkdir(output_dir)


class TestProject(unittest.TestCase):

    def test_one(self):
        dn = os.path.join(output_dir, 'proj_test_project')
        logger.debug('Running TestProject.test_one')
        if os.path.exists(dn):
            shutil.rmtree(dn)
        os.makedirs(dn)
        try:
            p = base_project.BaseProject(
                directory=dn,
                files_and_ip={
                    'design_files': [os.path.join(dir_path, 'testA.vhd')],
                    'simulation_files': [os.path.join(dir_path, 'testA.vhd')],
                    'ips': [],
                    'top_module': 'TestA',
                    }
            )
            v = vivado_project.VivadoProject(p)
            t = v.tasks_collection.get_most_recent_task()
            t.wait(raise_errors=False)
            errors = t.get_errors()
            self.assertTrue(len(errors) == 0)
        finally:
            pass
            #shutil.rmtree(dn)


if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    unittest.main()
