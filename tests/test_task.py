import unittest
import os
import shutil
import logging

from pyvivado import task, config, tasks_collection, vivado_task, shell_task

logger = logging.getLogger(__name__)

dir_path = os.path.dirname(os.path.realpath(__file__))
testdir = os.path.join(dir_path, '..', 'test_outputs')
if not os.path.exists(testdir):
    os.mkdir(testdir)

class TestTask(unittest.TestCase):

    def test_one(self):
        logger.debug('Running TestTask.test_one')
        task_directory = os.path.join(testdir, 'testtask')
        if os.path.exists(task_directory):
            shutil.rmtree(task_directory)
        os.makedirs(task_directory)
        collection = tasks_collection.TasksCollection(task_directory)
        description = 'dummy tast'
        t = task.Task.create(collection=collection, description=description)
        t2 = task.Task(t.directory)
        self.assertEqual(t2.get_description(), description)

    def test_error_catching(self):
        task_directory = os.path.join(testdir, 'testerrorcatching')
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

    def test_shell_task(self):
        logger.debug('Running TestTask.test_shell_task')
        task_directory = os.path.join(testdir, 'testtask')
        if os.path.exists(task_directory):
            shutil.rmtree(task_directory)
        os.makedirs(task_directory)

        def run_task(argument):
            collection = tasks_collection.TasksCollection(task_directory)
            description = 'dummy task'
            command = '{} {} {}'.format(
                'bash',
                os.path.join(config.shdir, 'dummy_test.sh'),
                argument,
                )
            t = shell_task.ShellTask.create(
                collection=collection, description=description,
                command_text=command)
            t.run_and_wait(raise_errors=False)
            return t

        t = run_task('fish')
        errors = t.get_errors()
        self.assertTrue(len(errors) == 0)
        msgs = t.get_messages()
        self.assertTrue(len(msgs) == 2)

        t2 = run_task('bison')
        errors = t2.get_errors()
        self.assertTrue(len(errors) == 1)


if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    unittest.main()

