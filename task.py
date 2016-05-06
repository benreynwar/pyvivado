import os
import logging

logger = logging.getLogger(__name__)


class Task:
    '''
    A task is an external process that we run.
    Each task has it's own directory created for it.
    This directory contains the following files:
     - current_state.txt - either NOT_STARTED, RUNNING, FINISHED_OK,
         FINISHED_ERROR.
     - final_state.txt either FINISHED_OK or FINISHED_ERROR
    '''
    POSSIBLE_STATES = ('NOT_STARTED', 'RUNNING', 'FINISHED_OK',
                       'FINISHED_ERROR')

    @classmethod
    def create(cls, collection, description=None):
        '''
        Create a new task.  Mostly just creating the directory and stuff like
        that.  Subclasses of this do the real work.

        Args:
            `parent_directory`: The directory in which we place create the
                tasks directory.
            `description`: Describes the task.
        '''
        directory = collection.get_next_directory()
        # We expect directory to exist and be empty.
        if not os.path.exists(directory):
            raise Exception('Directory does not exists: {}'.format(directory))
        if os.listdir(directory) != []:
            raise Exception('Directory is not empty: {}'.format(directory))
        t = cls(directory)
        if description is not None:
            t.set_description(description)
        t.set_current_state('NOT_STARTED')
        return t

    def current_state_fn(self):
        '''
        The filename where the task writes its state.
        '''
        fn = os.path.join(self.directory, 'current_state.txt')
        return fn

    def set_current_state(self, state):
        '''
        Sets the state in the state file.
        '''
        fn = self.current_state_fn()
        if state not in self.POSSIBLE_STATES:
            raise ValueError('State of {} is unknown.'.format(state))
        with open(fn, 'w') as f:
            f.write(state)

    def get_current_state(self):
        '''
        Get the current state of this task.
        '''
        fn = self.current_state_fn()
        with open(fn, 'r') as f:
            state = f.read().strip()
        if state not in self.POSSIBLE_STATES:
            raise ValueError('State of {} is unknown.'.format(state))
        return state

    def description_fn(self):
        '''
        The filename where the task writes its description.
        '''
        fn = os.path.join(self.directory, 'description.txt')
        return fn

    def set_description(self, description):
        fn = self.description_fn()
        with open(fn, 'w') as f:
            f.write(description)

    def get_description(self):
        fn = self.description_fn()
        if not os.path.exists(fn):
            description = None
        else:
            with open(fn, 'r') as f:
                description = f.read()
        return description

    def __init__(self, directory):
        '''
        Get the task corresponding to the passed directory.
        '''
        self.directory = directory
        self.description = self.get_description()
        if not os.path.exists(self.directory):
            raise Exception('Cannot find tasks directory {}'.format(
                self.directory))

    def get_stdout(self):
        stdout_fn = os.path.join(self.directory, 'stdout.txt')
        # Might not have been created yet.
        if os.path.exists(stdout_fn):
            with open(stdout_fn, 'r') as f:
                lines = f.readlines()
        else:
            lines = []
        return lines

    def get_stderr(self):
        stderr_fn = os.path.join(self.directory, 'stderr.txt')
        # We don't write this file in Windows.
        if os.path.exists(stderr_fn):
            with open(stderr_fn, 'r') as f:
                lines = f.readlines()
        else:
            lines = []
        return lines

    def is_finished(self):
        return os.path.exists(os.path.join(self.directory, 'finished.txt'))
