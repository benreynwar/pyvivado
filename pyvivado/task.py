import os
import logging
import time
import subprocess

from pyvivado import config

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

    # How to log different kinds of messages.
    MESSAGE_MAPPING = {
        'DEBUG': logger.debug,
        'INFO': logger.info,
        'WARNING': logger.warning,
        'ERROR': logger.error,
    }
    DEFAULT_FAILURE_MESSAGE_TYPES = (
        'ERROR',
        )

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
        self.process = None
        self.stdout = None
        self.stderr = None

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
        finished_fn = os.path.join(self.directory, 'finished.txt')
        return os.path.exists(finished_fn)

    def get_messages(self, ignore_strings=config.default_ignore_strings):
        '''
        Get any messages that the process wrote to it's output.
        and work out what type of message they were (e.g. ERROR, INFO...).

        Args:
            `ignore_strings`: Is a list of strings which when present in
                messages we ignore.
        '''
        messages = []
        out_lines = (self.get_stdout(), self.get_stderr())
        for lines in out_lines:
            for line in lines:
                ignore_line = False
                for ignore_string in ignore_strings:
                    if ignore_string in line:
                        ignore_line = True
                if not ignore_line:
                    for mt, logger_function in self.MESSAGE_MAPPING.items():
                        if line.startswith(mt):
                            messages.append((mt, line[len(mt)+1:-1]))
        return messages

    def log_messages(self, messages):
        '''
        Pass the messages to the python logger.
        '''
        for mt, message in messages:
            self.MESSAGE_MAPPING[mt](message)

    def get_errors(
            self, failure_message_types=DEFAULT_FAILURE_MESSAGE_TYPES):
        '''
        Get any errors that this Bash process has logged.
        '''
        errors = []
        messages = self.get_messages()
        for message_type, message in messages:
            if message_type in failure_message_types:
                errors.append(message)
        return errors

    def get_errors_and_warnings(
            self, failure_message_types=DEFAULT_FAILURE_MESSAGE_TYPES):
        '''
        Get any errors or warning that this Bash process has logged.
        '''
        errors = []
        messages = self.get_messages()
        for message_type, message in messages:
            if message_type in failure_message_types:
                errors.append(message)
        return errors

    def wait(self, sleep_time=1, raise_errors=True,
             failure_message_types=DEFAULT_FAILURE_MESSAGE_TYPES):
        '''
        Block python until this task has finished.
        '''
        finished = self.is_finished()
        if not finished:
            description = '' if self.description is None else self.description
            logger.debug("Waiting for task to finish: {}".format(description))
        while not finished:
            time.sleep(sleep_time)
            finished = self.is_finished()
        self.close_files()
        messages = self.get_messages()
        for mt, message in messages:
            self.MESSAGE_MAPPING[mt](message)
        if raise_errors:
            for mt, message in messages:
                if mt in failure_message_types:
                    raise Exception('Task Error: {}'.format(message))
        if self.get_current_state() != 'FINISHED_OK':
            raise Exception('Task did not finish correctly.')

    def close_files(self):
        if self.stdout is not None:
            self.stdout.close()
        if self.stderr is not None:
            self.stderr.close()

    def run_and_wait(self, sleep_time=1, raise_errors=True):
        '''
        Start the task and block python until the task has finished.
        Also log the output from the process.

        TODO: It would be nicer if this logged the output as the
        process was running instead of waiting until it was finished.
        '''
        self.run()
        self.wait(sleep_time=sleep_time, raise_errors=raise_errors)

    def monitor_output(self):
        '''
        Waits for the task to finish while logging the output.

        FIXME: I'm not using this much but I can't remember why.
        Should look into it.
        '''
        stdout_length = 0
        stderr_length = 0
        finished = False
        while not finished:
            finished = self.is_finished()
            stdout = self.get_stdout()
            stderr = self.get_stderr()
            if len(stdout) > stdout_length:
                for line in stdout[stdout_length:]:
                    logger.info(line[:-1])
            if len(stderr) > stderr_length:
                for line in stderr[stderr_length:]:
                    logger.error(line[:-1])
            stdout_length = len(stdout)
            stderr_length = len(stderr)
            time.sleep(1)

    def launch_unix_subprocess(self, commands, stdout_fn, stderr_fn):
        self.stdout = open(stdout_fn, 'w')
        self.stderr = open(stderr_fn, 'w')
        logger.debug(commands)
        self.process = subprocess.Popen(
            commands,
            stdout=self.stdout,
            stderr=self.stderr,
        )
