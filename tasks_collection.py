import fnmatch
import os
import logging
import time

from pyvivado import task

logger = logging.getLogger(__name__)


class TasksCollection(object):

    def __init__(self, directory, task_type=task.Task):
        self.directory = directory
        self.task_type = task_type

    def get_ids(self):
        ids = [int(fn[5:]) for fn in os.listdir(self.directory)
               if fnmatch.fnmatch(fn, 'task_*')]
        return ids

    def get_tasks(self):
        '''
        Get all the tasks that have been run on this project.
        We get them from their directories in the project directory rather
        than from checking the `tasks_collection`.
        '''
        ids = self.get_ids()
        tasks = [self.task_type(self.id_to_directory(_id)) for _id in ids]
        return tasks

    def unfinished_tasks(self):
        '''
        Gets a list of all tasks on this project that have not finished.
        '''
        tasks = [t for t in self.get_tasks() if not t.is_finished()]
        return tasks

    def get_most_recent_task(self):
        '''
        Get the most recent task that was run on this project.
        '''
        _id = self.get_last_index()
        t = self.task_type(self.id_to_directory(_id))
        return t

    def wait_for_most_recent_task(self):
        '''
        Get the most recent task that was run on this project and wait
        for it to complete.
        '''
        t = self.get_most_recent_task()
        while not t.is_finished():
            logger.debug('Waiting for tasks to finish.')
            time.sleep(1)
        t.log_messages(t.get_messages())
        return t

    def get_last_index(self):
        ids = sorted(self.get_ids())
        if len(ids) == 0:
            last_index = -1
        else:
            last_index = ids[-1]
        return last_index

    def id_to_directory(self, id):
        return os.path.join(self.directory, 'task_{}'.format(id))

    def get_last_directory(self):
        last_index = self.get_last_index()
        fn = self.id_to_directory(last_index)
        return fn

    def get_next_directory(self):
        last_index = self.get_last_index()
        fn = self.id_to_directory(last_index+1)
        os.mkdir(fn)
        return fn
