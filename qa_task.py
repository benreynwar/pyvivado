import unittest
import os
import shutil
import logging
import time

from pyvivado import task, config

logger = logging.getLogger('pyvivado.test_task')


class TestTask(unittest.TestCase):

    def test_one(self):
        logger.debug('Running TestTask.test_one')
        parent_directory = os.path.join(config.testdir, 'testtask')
        if os.path.exists(parent_directory):
            shutil.rmtree(parent_directory)
        os.makedirs(parent_directory)
        tasks_collection = config.default_tasks_collection
        tasks_collection.drop()
        t = task.Task.create(parent_directory, tasks_collection)
        self.assertEqual(tasks_collection.count(), 1)
        record = tasks_collection.find_by_id(t._id)
        self.assertEqual(record['parent_directory'], parent_directory)

    def test_killing(self):
        parent_directory = os.path.join(config.testdir, 'testkilling')
        if os.path.exists(parent_directory):
            shutil.rmtree(parent_directory)
        os.makedirs(parent_directory)
        dummy_fn = os.path.join(parent_directory, 'dummy.txt')
        command = '::pyvivado::loop_forever {{{}}}'.format(dummy_fn)
        tasks_collection = config.default_tasks_collection
        tasks_collection.drop()
        t = task.VivadoTask.create(
            parent_directory, command, tasks_collection,
            description='Create a vivado task in an infinte loop')
        t.run()
        # Wait for a bit so it can write stuff.
        time.sleep(3)
        with open(dummy_fn, 'r') as f:
            dummy_text = f.read()
        
if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    unittest.main()

