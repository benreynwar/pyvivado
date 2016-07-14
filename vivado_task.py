import logging
import os
import subprocess
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
        if os.name == 'nt':
            commands = [config.vivado, '-log', stdout_fn, '-mode', 'batch',
                        '-source', command_fn]
            logger.debug('running vivado task in directory {}'.format(self.directory))
            logger.debug('command is {}'.format(' '.join(commands)))
            self.process = subprocess.Popen(
                commands,
                # So that process stays alive when terminal is closed
                # in Windows.
                # Commented out because doesn't seem to be working now.
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            logger.debug('started process')
        else:
            commands = [config.vivado, '-mode', 'batch', '-source',
                        command_fn]
            self.launch_unix_subprocess(
                commands, stdout_fn=stdout_fn, stderr_fn=stderr_fn)
        os.chdir(cwd)
