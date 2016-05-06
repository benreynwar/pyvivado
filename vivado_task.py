import logging
import os
import subprocess
import time
import warnings

from pyvivado import task, config

logger = logging.getLogger(__name__)


class VivadoTask(task.Task):
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
    DEFAULT_FAILURE_MESSAGE_TYPES = (
        'CRITICAL_WARNING', 'ERROR', 'FATAL_ERROR', 'Failure')

    @classmethod
    def create(cls, collection, command_text, description=None):
        '''
        Create the files necessary for the Vivado process.

        Args:
           collection: A TasksCollection in which the task is to be added.
           command_text: The TCL command we will execute.
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
        logger.debug('Creating a new VivadoTask in directory {}'.format(
            collection.directory))
        logger.debug('Command is {}'.format(command_text))
        t = super().create(collection=collection, description=description)
        # Create the command file.
        command_fn = os.path.join(t.directory, 'command.tcl')
        with open(command_fn, 'w') as f:
            f.write(command)
        return t

    def __init__(self, directory):
        super().__init__(directory=directory)

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

    def wait(self, sleep_time=1, raise_errors=True,
             failure_message_types=DEFAULT_FAILURE_MESSAGE_TYPES):
        '''
        Block python until this task has finished.
        '''
        finished = self.is_finished()
        while not finished:
            time.sleep(sleep_time)
            finished = self.is_finished()
            logger.debug("Waiting for task to finish.")
        messages = self.get_messages()
        for mt, message in messages:
            self.MESSAGE_MAPPING[mt](message)
        if raise_errors:
            for mt, message in messages:
                if mt in failure_message_types:
                    raise Exception('Task Error: {}'.format(message))

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
