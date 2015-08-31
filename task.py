import os
import datetime
import subprocess
import logging
import time
import warnings

from pyvivado import config

logger = logging.getLogger(__name__)


class Task:
    '''
    A task is an external process that we run.
    Each task has it's own directory created for it.
    This directory contains the following files:
     - current_state.txt - either NOT_STARTED, RUNNING, FINISHED_OK, FINISHED_ERROR.
     - final_state.txt either FINISHED_OK or FINISHED_ERROR
    '''
    POSSIBLE_STATES = ('NOT_STARTED', 'RUNNING', 'FINISHED_OK',
                       'FINISHED_ERROR')

    @classmethod
    def create(cls, parent_directory, tasks_collection, description=None):
        '''
        Create a new task.  Mostly just setting the database entry up,
        creating the directory and stuff like that.  Subclasses of this
        do the real work.
        
        Args:
            `parent_directory`: The directory in which we place create the
                tasks directory.
            `tasks_collection`: How we keep track of tasks.
            `description`: Describes the task.
        '''
        if not os.path.exists(parent_directory):
            raise ValueError(
                'Parent directory of task ({}) does not exist'.format(
                    parent_directory))
        record = {
            'parent_directory': parent_directory,
            'description': description,
            'state': 'NOT_STARTED',
        }
        task_id = tasks_collection.insert(record)
        _id = str(record['id'])
        dn = 'task_' + _id
        directory = os.path.join(parent_directory, dn)
        os.mkdir(directory)
        t = cls(_id=record['id'], tasks_collection=tasks_collection)
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

    def __init__(self, _id, tasks_collection):
        '''
        Get the task corresponding to the passed id.
        '''
        self.record = tasks_collection.find_by_id(_id)
        self._id = str(self.record['id'])
        self.parent_directory = self.record['parent_directory']
        self.description = self.record.get('description', '')
        if not os.path.exists(self.parent_directory):
            raise Exception(
                'Cannot find tasks parent directory {}'
                .format(self.parent_directory))
        dn = 'task_' + self._id
        self.directory = os.path.join(self.parent_directory, dn)
        if not os.path.exists(self.directory):
            raise Exception(
                'Cannot find tasks directory {}'
                .format(self.directory))
        


class VivadoTask(Task):
    '''
    A python wrapper to keep track of a spawned Vivado process.
    '''

    # How to log different kinds of Vivado messages.
    MESSAGE_MAPPING = {
        'DEBUG': logger.debug,
        'INFO': logger.info,
        'WARNING': logger.warning,
        'CRITICAL WARNING': logger.error,
        'ERROR': logger.error,
        'FATAL_ERROR': logger.error,
        # This is a hack to get 'assert's in the HDL with severity 'Failure'
        # to log an error message.
        'Failure': logger.error,
    }

    @classmethod
    def create(cls, parent_directory, command_text, tasks_collection,
               description=None):
        '''
        Create the files necessary for the Vivado process.
        
        Args:
           parent_directory: The directory of the Vivado project.
           command_text: The TCL command we will execute.
           tasks_collection: How we keep track of Vivado processes.
           description: A description of this task.
        '''
        # Generate the TCL script that this Vivado process will run.
        command_template_fn = os.path.join(config.tcldir, 'vivado_task.tcl.t')
        with open(command_template_fn, 'r') as f:
            command_template = f.read()
        command = command_template.format(
            tcl_directory=config.tcldir,
            command=command_text
        )
        # Make parent directory absolute
        logger.debug('Creating a new VivadoTask in directory {}'.format(parent_directory))
        logger.debug('Command is {}'.format(command_text))
        t = super().create(parent_directory=parent_directory,
                           description=description,
                           tasks_collection=tasks_collection)
        # Create the command file.
        command_fn = os.path.join(t.directory, 'command.tcl')
        with open(command_fn, 'w') as f:
            f.write(command)
        return t

    def __init__(self, _id, tasks_collection):
        super().__init__(_id=_id, tasks_collection=tasks_collection)
        
    def run(self):
        '''
        Spawn the process that will run the vivado process.
        '''
        cwd = os.getcwd()
        os.chdir(self.directory)
        stdout_fn = 'stdout.txt' 
        stderr_fn = 'stderr.txt' 
        command_fn = 'command.tcl' 
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            DETACHED_PROCESS = 8
            if os.name == 'nt':
                commands = [config.vivado, '-log', stdout_fn, '-mode', 'batch',
                            '-source', command_fn]
                p = subprocess.Popen(
                    commands,
                    # So that process stays alive when terminal is closed
                    # in Windows.
                    creationflags=DETACHED_PROCESS,
                )
            else:
                commands = [config.vivado, '-mode', 'batch', '-source',
                            command_fn]
                p = subprocess.Popen(
                    commands,
                    stdout=open(stdout_fn, 'w'),
                    stderr=open(stderr_fn, 'w'),
                )
                
        os.chdir(cwd)

    def get_messages(self, ignore_strings=config.default_ignore_strings):
        '''
        Get any messages that the vivado process wrote to it's output.
        and work out what type of message they were (e.g. ERROR, INFO...).
        
        Args:
            `ignore_strings`: Is a list of strings which when present in
                Vivado messages we ignore.
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
                       
    def get_errors(self):
        '''
        Get any errors that this Vivado process has logged.
        '''
        errors = []
        messages = self.get_messages()
        for message_type, message in messages:
            if message_type in ('FATAL_ERROR', 'ERROR', 'CRITICAL WARNING', 'Failure'):
                errors.append(message)
        return errors

    def get_errors_and_warnings(self):
        '''
        Get any errors or warning that this Vivado process has logged.
        '''
        errors = []
        messages = self.get_messages()
        for message_type, message in messages:
            if message_type in ('FATAL_ERROR', 'ERROR', 'CRITICAL WARNING', 'WARNING', 'Failure'):
                errors.append(message)
        return errors

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

    def wait(self, sleep_time=1):
        '''
        Block python until this task has finished.
        '''
        finished = self.is_finished()
        while not finished:
            time.sleep(sleep_time)
            finished = self.is_finished()
            logger.debug("Waiting for task to finish.")

    def run_and_wait(self, sleep_time=1):
        '''
        Start the task and block python until the task has finished.
        Also log the output from the process.

        TODO: It would be nicer if this logged the output as the
        process was running instead of waiting until it was finished.
        '''
        self.run()
        self.wait(sleep_time=sleep_time)
        self.log_messages(self.get_messages())

    def monitor_output(self):
        '''
        Waits for the task to finish while logging the output.

        FIXME: I'm not using this much but I can't remember why.
        Should look into it.
        '''
        stdout_length = 0
        stderr_length = 0
        finished = False
        while (not finished):
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
        
