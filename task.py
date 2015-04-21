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
     - task_script.* - run to start the process
     - task_details.txt - information like starting time.  This is just so this
         information can be conveniently accessed from the file system.
     - current_state.txt - either NOT_STARTED, RUNNING, FINISHED_OK, FINISHED_ERROR.
     - log.txt - contains DEBUG, INFO, WARNING and ERROR lines.
     - final_state.txt either FINISHED_OK or FINISHED_ERROR
    '''
    POSSIBLE_STATES = ('NOT_STARTED', 'RUNNING', 'FINISHED_OK',
                       'FINISHED_ERROR')

    @classmethod
    def create(cls, parent_directory, tasks_collection, description=None):
        logger.debug('Creating a new Task')
        if not os.path.exists(parent_directory):
            raise ValueError(
                'Parent directory of task ({}) does not exist'.format(
                    parent_directory))
        record = {
            'parent_directory': parent_directory,
            'description': description,
            'state': 'NOT_STARTED',
        }
        logger.debug('Inserting the record {}.'.format(record))
        task_id = tasks_collection.insert(record)
        _id = str(record['id'])
        logger.debug('The id is {}'.format(_id))
        dn = 'task_' + _id
        directory = os.path.join(parent_directory, dn)
        os.mkdir(directory)
        t = cls(_id=record['id'], tasks_collection=tasks_collection)
        t.set_current_state('NOT_STARTED')
        return t
        
    def current_state_fn(self):
        fn = os.path.join(self.directory, 'current_state.txt')
        return fn

    def set_current_state(self, state):
        fn = self.current_state_fn()
        if state not in self.POSSIBLE_STATES:
            raise ValueError('State of {} is unknown.'.format(state))
        with open(fn, 'w') as f:
            f.write(state)
        

    def get_current_state(self):
        fn = self.current_state_fn()
        with open(fn, 'r') as f:
            state = f.read().strip()
        if state not in self.POSSIBLE_STATES:
            raise ValueError('State of {} is unknown.'.format(state))
        return state

    def __init__(self, _id, tasks_collection):
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

    MESSAGE_MAPPING = {
        'DEBUG': logger.debug,
        'INFO': logger.info,
        'WARNING': logger.warning,
        'CRITICAL WARNING': logger.error,
        'ERROR': logger.error,
        'FATAL_ERROR': logger.error,
    }

    @classmethod
    def create(cls, parent_directory, command_text, tasks_collection,
               description=None):
        command_template = '''
if {{[catch {{
  lappend auto_path {{{tcl_directory}}}
  puts $auto_path
  package require pyvivado
  {command}
  }} message]}} {{
  puts "ERROR: $message"
}}
set filename finished 
set fileId [open $filename "w"]
close $fileId  
'''
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
        cwd = os.getcwd()
        os.chdir(self.directory)
        stdout_fn = 'stdout.txt' #os.path.join(self.directory, 'stdout.txt')
        stderr_fn = 'stderr.txt' #os.path.join(self.directory, 'stderr.txt')
        command_fn = 'command.tcl' #os.path.join(self.directory, 'command.tcl')        
        commands = [config.vivado, '-mode', 'batch', '-source', command_fn]
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            p = subprocess.Popen(
                commands,
                stdout=open(stdout_fn, 'w'),
                stderr=open(stderr_fn, 'w'),)
        os.chdir(cwd)

    def get_messages(self):
        ignore_strings = (
            # Ignore warnings about invalid parts
            'as part xc7k325tffg900-2 specified in board_part file is either',
            'as part xc7z045ffg900-2 specified in board_part file is either',
            # Ignore Webtalk communication problems
            '[XSIM 43-3294] Signal EXCEPTION_ACCESS_VIOLATION received',
            # Ignore Warnings from Xilinx DDS Compiler
            '"/proj/xhdhdstaff/saikatb/verific_integ/data/vhdl/src/ieee/distributable/numeric_std.vhd" Line 2547. Foreign attribute on subprog "<=" ignored',
            '"/proj/xhdhdstaff/saikatb/verific_integ/data/vhdl/src/ieee/distributable/numeric_std.vhd" Line 2895. Foreign attribute on subprog "=" ignored',
            # Ignore timescale warnings
            "has a timescale but at least one module in design doesn't have timescale.",
        )
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
        for mt, message in messages:
            self.MESSAGE_MAPPING[mt](message)
                       
    def get_errors(self):
        errors = []
        messages = self.get_messages()
        for message_type, message in messages:
            if message_type in ('FATAL_ERROR', 'ERROR', 'CRITICAL WARNING'):
                errors.append(message)
        return errors

    def get_errors_and_warnings(self):
        errors = []
        messages = self.get_messages()
        for message_type, message in messages:
            if message_type in ('FATAL_ERROR', 'ERROR', 'CRITICAL WARNING', 'WARNING'):
                errors.append(message)
        return errors

    def get_stdout(self):
        stdout_fn = os.path.join(self.directory, 'stdout.txt')
        with open(stdout_fn, 'r') as f:
            lines = f.readlines()
        return lines

    def get_stderr(self):
        stdout_fn = os.path.join(self.directory, 'stderr.txt')
        with open(stdout_fn, 'r') as f:
            lines = f.readlines()
        return lines        

    def is_finished(self):
        return os.path.exists(os.path.join(self.directory, 'finished'))

    def wait(self, sleep_time=1):
        finished = self.is_finished()
        while not finished:
            time.sleep(sleep_time)
            finished = self.is_finished()
            logger.debug("Waiting for task to finish.")

    def run_and_wait(self, sleep_time=1):
        self.run()
        self.wait(sleep_time=sleep_time)
        self.log_messages(self.get_messages())

    def monitor_output(self):
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
        
