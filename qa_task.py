import unittest
import os
import shutil
import logging

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

if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    unittest.main()

