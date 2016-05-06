import unittest
import os
import shutil
import logging

from pyvivado import task, config, tasks_collection, vivado_task

logger = logging.getLogger(__name__)


class TestTask(unittest.TestCase):

    def test_one(self):
        logger.debug('Running TestTask.test_one')
        task_directory = os.path.join(config.testdir, 'testtask')
        if os.path.exists(task_directory):
            shutil.rmtree(task_directory)
        os.makedirs(task_directory)
        collection = tasks_collection.TasksCollection(task_directory)
        description = 'dummy tast'
        t = task.Task.create(collection=collection, description=description)
        t2 = task.Task(t.directory)
        self.assertEqual(t2.get_description(), description)

    def test_error_catching(self):
        task_directory = os.path.join(config.testdir, 'testerrorcatching')
        if os.path.exists(task_directory):
            shutil.rmtree(task_directory)
        os.makedirs(task_directory)
        collection = tasks_collection.TasksCollection(task_directory)
        t = vivado_task.VivadoTask.create(
            collection=collection,
            description='test error catching task',
            command_text='Totally invalid command text.  We should get an error.',
        )
        self.assertEqual(collection.count(), 1)
        t.run_and_wait(raise_errors=False)
        errors = t.get_errors()
        self.assertTrue(len(errors) > 0)


if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    unittest.main()

