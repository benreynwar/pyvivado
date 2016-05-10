import logging
import os
import subprocess
import time
import warnings

from pyvivado import task, config

logger = logging.getLogger(__name__)


class ShellTask(task.Task):
    '''
    A python wrapper to keep track of a spawned process.
    '''

    @classmethod
    def create(cls, collection, command_text, description=None):
        '''
        Create the files necessary for the process.

        Args:
           collection: A TasksCollection in which the task is to be added.
           command_text: The TCL command we will execute.
           description: A description of this task.
        '''
        # Generate the shell script that this process will run.
        command_template_fn = os.path.join(config.shdir, 'task.sh.t')
        with open(command_template_fn, 'r') as f:
            command_template = f.read()
        command = command_template.format(
            sh_directory=config.shdir,
            command=command_text
        )
        logger.debug('Creating a new ShellTask in directory {}'.format(
            collection.directory))
        logger.debug('Command is {}'.format(command_text))
        t = super().create(collection=collection, description=description)
        # Create the command file.
        command_fn = os.path.join(t.directory, 'command.sh')
        with open(command_fn, 'w') as f:
            f.write(command)
        return t

    def __init__(self, directory):
        super().__init__(directory=directory)

    def run(self):
        '''
        Spawn the process.
        '''
        cwd = os.getcwd()
        os.chdir(self.directory)
        stdout_fn = 'stdout.txt'
        stderr_fn = 'stderr.txt'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            if os.name == 'nt':
                raise ValueError('Shell Tasks not implemented for Windows')
            else:
                self.launch_unix_subprocess(
                    ['bash', './command.sh'], stdout_fn=stdout_fn, stderr_fn=stderr_fn)
        os.chdir(cwd)
