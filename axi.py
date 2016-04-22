'''
Python tools for creating and parsing AXI communications.
'''

import asyncio
import random
import logging
import time

from pyvivado import signal

logger = logging.getLogger(__name__)

# `Comm` objects are registered here by the name of the module they are
# responsible for communicating with.
module_register = {}

# Response code for AXI.
OKAY = 0
EXOKAY = 1
SLVERR = 2
DECERR = 3

# Define a record type for Master-to-Slave AXI
axi4lite_m2s_type = signal.Record(
    contained_types=(
        ('araddr', signal.StdLogicVector(width=32)),
        ('arprot', signal.StdLogicVector(width=3)),
        ('arvalid', signal.std_logic_type),
        ('awaddr', signal.StdLogicVector(width=32)),
        ('awprot', signal.StdLogicVector(width=3)),
        ('awvalid', signal.std_logic_type),
        ('bready', signal.std_logic_type),
        ('rready', signal.std_logic_type),
        ('wdata', signal.StdLogicVector(width=32)),
        ('wstrb', signal.StdLogicVector(width=4)),
        ('wvalid', signal.std_logic_type),
    ),
    name='axi4lite_m2s',
)

# Define a record type for Slave-to-Master AXI
axi4lite_s2m_type = signal.Record(
    contained_types=(
        ('arready', signal.std_logic_type),
        ('awready', signal.std_logic_type),
        ('bresp', signal.StdLogicVector(width=2)),
        ('bvalid', signal.std_logic_type),
        ('rdata', signal.StdLogicVector(width=32)),
        ('rresp', signal.StdLogicVector(width=2)),
        ('rvalid', signal.std_logic_type),
        ('wready', signal.std_logic_type),
    ),
    name='axi4lite_s2m',
)

def make_empty_axi4lite_m2s_dict():
    '''
    Creates and empty master-to-slave AXI dictionary.
    '''
    return {
        'araddr': 0,
        'arprot': None,
        'arvalid': 0,
        'awaddr': 0,
        'awprot': None,
        'awvalid': 0,
        'bready': 0,
        'rready': 0,
        'wdata': 0,
        'wstrb': None,
        'wvalid': 0,
    }


def make_empty_axi4lite_s2m_dict():
    '''
    Creates and empty slave-to-master AXI dictionary.
    '''
    return {
        'arready': 1,
        'awready': 1,
        'bresp': 0,
        'bvalid': 0,
        'rdata': 0,
        'rresp': 0,
        'rvalid': 0,
        'wready': 1,
    }

    
# Used to define whether AXI command are reading or writing.
READ_TYPE = 'READ'
WRITE_TYPE = 'WRITE'


class ConnCommandHandler(object):
    '''
    This handler receives `CommCommand` objects and sends their AXI
    commands over the passed in `Connection`.  The responses are
    then processed by the `CommCommand` object that send them.

    This handler is useful to simplify communication with the FPGA.
    '''

    def __init__(self, conn):
        '''
        `conn`: A `Connection` object that the handler uses to communicate
                with the FPGA.
        '''
        self.conn = conn

    def send(self, commands):
        '''
        Sends a list of `commands` where are CommCommand objects to the FPGA
        and processes the responses.
        '''
        for command in commands:
            if isinstance(command, FakeWaitCommand):
                time.sleep(command.sleep_time)
            rs = []
            for ac in command.axi_commands:
                assert(ac.readorwrite in (WRITE_TYPE, READ_TYPE))
                if ac.readorwrite == WRITE_TYPE:
                    if ac.constant_address:
                        r = self.conn.write_repeat(address=ac.start_address,
                                              data=ac.data)
                    else:
                        r = self.conn.write(address=ac.start_address, data=ac.data)
                else:
                    if ac.constant_address:
                        raise Exception('Reading from constant address not supported yet.')
                    else:
                        r = self.conn.read(address=ac.start_address, length=ac.length)
                rs.append(r)
            command.process_response((None, rs))


class DictCommandHandler(object):
    '''
    This handler receives `CommCommand` objects and stores them.
    When the `make_command_dicts` method is called the handler returns
    a list of AXI master-to-slave dictionaries that specify the commands.
    It can also parse the output AXI slave-to-master dictionaries from
    a simulation.

    This handler is useful to fake communication when running simulations.
    '''
    
    def __init__(self):
        self.unsent_commands = []
        self.sent_commands = []

    def send(self, commands):
        self.unsent_commands += commands

    def make_command_dicts(self):
        '''
        Generates slave-to-master AXI dictionaries from the CommCommands
        that have been given to the handler.  These dictionaries can
        be passed as input to simluations.
        '''
        ds = []
        while self.unsent_commands:
            command = self.unsent_commands.pop(0)
            if isinstance(command, FakeWaitCommand):
                for i in range(command.clock_cycles):
                    ds.append(make_empty_axi4lite_m2s_dict())
            for ac in command.axi_commands:
                for index in range(ac.length):
                    d = make_empty_axi4lite_m2s_dict()
                    if ac.constant_address:
                        address = ac.start_address
                    else:
                        address = ac.start_address + index
                    if ac.readorwrite == READ_TYPE:
                        d['araddr'] = address
                        d['arvalid'] = 1
                    else:
                        d['awaddr'] = address
                        d['awvalid'] = 1
                        d['wvalid'] = 1
                        d['wdata'] = ac.data[index]
                    ds.append(d)
            self.sent_commands.append(command)
        return ds

    def consume_response_dicts(self, ds):
        '''
        Takes a list of slave-to-master dictionaries obtained from
        a simulation and processes them using the 'CommCommand' objects
        that sent them.

        If their was a bug in the AXI communication (i.e. no response
        when their should have been), then things can get out of sync,
        and the wrong 'CommCommand' objects will process the wrong responses.
        '''
        for command in self.sent_commands:
            results = []
            first_e = None
            for ac in command.axi_commands:
                error_help = ' Command description: {}'.format(ac.description)
                bad_response = False
                rs = []
                e = None
                for index in range(ac.length):
                    r = None
                    while r is None:
                        if len(ds) == 0:
                            raise Exception('DictCommandHandler is out of sync.  Probably a bug in the AXI communication.' + error_help)
                        d = ds.pop(0)
                        r = None
                        if ac.readorwrite == READ_TYPE:
                            if d['rvalid']:
                                r = (d['rresp'], d['rdata'])
                        elif ac.readorwrite == WRITE_TYPE:
                            if d['bvalid']:
                                r = (d['bresp'], None)
                    if r[0] != OKAY:
                        bad_response = True
                    rs.append(r)
                if ac.readorwrite == WRITE_TYPE:
                    if len(rs) != ac.length:
                        e = Exception('Incorrect number of response.' + error_help)
                    elif bad_response:
                        e = Exception('Received a bad response.' + error_help)
                    result = None
                else:
                    if bad_response:
                        e = Exception('Received a bad response.' + error_help)
                        result = None
                    else:
                        result = [r[1] for r in rs]
                if first_e is None and e is not None:
                    first_e = e
                results.append(result)
            command.process_response((first_e, results))


class AxiCommand(object):
    '''
    Defines a series AXI4Lite master-to-slave commands.
    '''

    def __init__(self, start_address, length, readorwrite, data=None,
                 constant_address=False, description=None):
        '''
        `start_address`: The address on which the first AXI command operates.
        `constant_address`: If this is `True` we keep operating on the same
             address, otherwise we increment.
        `length`: The number of commands.
        `readorwrite`: Can be either `READ_TYPE` or `WRITE_TYPE`.
        'data': A list of integers to send (if it is a write command).
        `description`: An optional description for debugging purposes.
        '''
        max_address = pow(2, 32-1)
        self.start_address = start_address
        self.length = length
        self.readorwrite = readorwrite
        self.constant_address = constant_address
        self.description = description
        assert(readorwrite in (READ_TYPE, WRITE_TYPE))
        self.data = data
        if readorwrite == READ_TYPE:
            assert(self.data is None)
        else:
            assert(len(self.data) == length)
        assert(start_address <= max_address)
        if not constant_address:
            assert(start_address + length-1 <= max_address)
    
        
class CommCommand(object):
    '''
    Defines a list of `AXICommand`s along with methods to
    parse the response.
    '''

    def __init__(self, description=None):
        # The futures attibute is populated with the result when
        # it is processed.
        # See asynio for details on futures.  But basically
        # future.done() tells you if it is finished and
        # future.result() will give you the result.
        
        # We use futures here so that we can create and send commands
        # but not expect to receive results immediately.  This is 
        # particularly useful during simulation when we create and
        # send all the commands before the simulation starts. But
        # obviously can't process the responses until after the 
        # simulation is finished.
        self.future = asyncio.Future()
        self.description = description

    def process_result(self, result):
        '''
        Processes the results from the AXI commands and returns
        an (Exception, result) Tuple.
        '''
        return None, result

    def process_response(self, response):
        '''
        Takes an (Exception, result) tuple and sets the exception
        and result on the future.
        '''
        e, result = response
        if e is not None:
            self.future.set_exception(e)
        else:
            e, processed_result = self.process_result(result)
            if e is not None:
                self.future.set_exception(e)
            else:
                self.future.set_result(processed_result)

    def set_unsigneds_commands(
            self, values, address, description=None, constant_address=False):
        '''
        Create `AxiCommand`s for writing unsigned integers.
        '''
        for value in values:
            assert(value < pow(2, 32))
        command = AxiCommand(
            start_address=address,
            length=len(values),
            readorwrite=WRITE_TYPE,
            data=values,
            constant_address=constant_address,
            description=description,
        )
        return [command]

    def set_signeds_commands(
            self, values, address, constant_address=False, description=None):
        '''
        Create `AxiCommand`s for writing signed integers.
        '''
        offset = pow(2, 32)
        unsigneds = [v+offset if v < 0 else v for v in values]
        return self.set_unsigneds_commands(
            unsigneds, address, constant_address, description=description)

    def get_unsigneds_commands(
            self, address, length=1, constant_address=False, description=None):
        '''
        Create `AxiCommand`s for reading unsigned integers.
        '''
        command = AxiCommand(
            start_address=address,
            length=length,
            readorwrite=READ_TYPE,
            constant_address=constant_address,
            description=description,
        )
        return [command]

    def set_unsigned_commands(self, value, address, description=None):
        '''
        Create `AxiCommand`s for writing an unsigned integer.
        '''
        return self.set_unsigneds_commands(
            values=[value], address=address, description=description)

    def set_signed_commands(
            self, value, address, constant_address=False, description=None):
        '''
        Create `AxiCommand`s for writing signed integers.
        '''
        if value < 0:
            value += pow(2, 32)
        return self.set_unsigned_commands(
            value, address, description=description)

    def trigger_commands(self, address, description=None):
        '''
        Create `AxiCommand`s for writing a 0 to an address.  This
        is used as a trigger sometimes.
        '''
        return self.set_unsigned_commands(0, address, description=description)

    def get_unsigned_commands(self, address, description=None):
        '''
        Create `AxiCommand`s for reading an unsigned integer.
        '''
        return self.get_unsigneds_commands(
            address, length=1, description=description)

    def get_boolean_commands(self, address, description=None):
        '''
        Create `AxiCommand`s for reading a boolean.
        '''
        command = AxiCommand(
            start_address=address,
            length=1,
            readorwrite=READ_TYPE,
            description=description)
        return [command]

    def process_get_boolean(self, result):
        '''
        Process a response from reading a boolean.
        '''
        e = None
        r = None
        if result == 1:
            r = True
        elif result == 0:
            r = False
        else:
            r = None
            e = Exception('Unknown return value ({}). Command Description: {}'.format(result, self.description))
        return e, r

    def set_boolean_commands(self, value, address, description=None):
        '''
        Create `AxiCommand`s for writing a boolean.
        '''
        assert(value in (True, False))
        if value:
            data = [1]
        else:
            data = [0]
        command = AxiCommand(
            start_address=address,
            length=1,
            readorwrite=WRITE_TYPE,
            data=data,
            description=description,
        )
        return [command]


class FakeWaitCommand(CommCommand):
    '''
    This is used when we're sending commands to a simulation.
    The `DictCommandHandler` translates it into a bunch of empty
    master-to-slave dictionaries.
    It can be also used when communicating with an FPGA to indicate
    a sleep time.  This is for compatibility of tests.
    '''

    def __init__(self, clock_cycles, sleep_time=0, description=None):
        super().__init__(description=description)
        self.clock_cycles = clock_cycles
        self.axi_commands = []
        self.sleep_time = sleep_time


class GetBooleanCommand(CommCommand):

    def __init__(self, address, description=None):
        super().__init__(description=description)
        self.axi_commands = self.get_boolean_commands(
            address=address, description=description)

    def process_result(self, result):
        return self.process_get_boolean(result[0][0])

class SetBooleanCommand(CommCommand):

    def __init__(self, value, address, description=None):
        super().__init__(description=description)
        self.axi_commands = self.set_boolean_commands(
            value=value, address=address, description=description)

class GetUnsignedCommand(CommCommand):

    def __init__(self, address, description=None):
        super().__init__(description=description)
        self.axi_commands = self.get_unsigned_commands(
            address=address, description=description)

    def process_result(self, result):
        return None, result[0][0]
    
class SetUnsignedCommand(CommCommand):

    def __init__(self, value, address, description=None):
        super().__init__(description=description)
        self.axi_commands = self.set_unsigned_commands(
            value=value, address=address, description=description)

class SetUnsignedsCommand(CommCommand):

    def __init__(self, values, address, constant_address=False, description=None):
        super().__init__(description=description)
        self.axi_commands = self.set_unsigneds_commands(
            values=values, address=address, constant_address=constant_address,
            description=description)

class TriggerCommand(CommCommand):
    
    def __init__(self, address, description=None):
        super().__init__(description=description)
        self.axi_commands = self.trigger_commands(
            address, description=description)


class CombinedCommands(CommCommand):
    '''
    Collects a number of `CommCommand` objects into a single one.

    The result returns is a list of the results of the contained
    `CommCommand` objects.
    '''

    def __init__(self, commands, description=None):
        super().__init__(description=description)
        self.subcommands = commands
        self.axi_commands = []
        for sc in self.subcommands:
            self.axi_commands += sc.axi_commands
        
    def process_result(self, result):
        new_result = []
        e = None
        for sc in self.subcommands:
            rs = []
            for ac in sc.axi_commands:
                rs.append(result.pop(0))
            sub_e, sub_r = sc.process_result(rs)
            if sub_e is not None and e is None:
                e = sub_e
            new_result.append(sub_r)
        return e, new_result
            

class Comm(object):
    '''
    Subclasses of this create python interfaces for specific module
    that create `CommCommand`s to send to a communications handler.
    '''

    def fake_wait(self, clock_cycles, sleep_time=0):
        command = FakeWaitCommand(
            clock_cycles=clock_cycles, sleep_time=sleep_time)
        self.handler.send([command])
        return command.future

    def get_boolean(self, address, description=None):
        command = GetBooleanCommand(address=address, description=description)
        self.handler.send([command])
        return command.future

    def set_boolean(self, value, address, description=None):
        command = SetBooleanCommand(
            value=value, address=address, description=description)
        self.handler.send([command])
        return command.future

    def get_unsigned(self, address, description=None):
        command = GetUnsignedCommand(address=address, description=description)
        self.handler.send([command])
        return command.future 

    def set_unsigned(self, value, address, description=None):
        command = SetUnsignedCommand(value=value, address=address,
                                     description=description)
        self.handler.send([command])
        return command.future 

    def set_unsigneds(
            self, values, address, constant_address=False, description=None):
        command = SetUnsignedsCommand(
            values=values, address=address, constant_address=constant_address,
            description=description)
        self.handler.send([command])
        return command.future 

    def trigger(self, address, description=None):
        command = TriggerCommand(address=address, description=description)
        self.handler.send([command])
        return command.future
       

class AxiDummy(object):
    '''
    Dummy axi module for using to create tests.
    '''

    MAX_PIPE_LENGTH = 10
    
    def __init__(self, max_pipe_length=1):
        self.reset()
        self.max_pipe_length = max_pipe_length

    def reset(self):
        self.write_counter = 0
        self.read_counter = 0

    def handle_write(self):
        logger.debug('writing')
        if self.write_counter:
            raise Exception('Received write before finished previous write.')
        self.write_counter = random.randint(2, self.max_pipe_length+1)

    def handle_read(self):
        if self.read_counter:
            raise Exception('Received read before finished previous read.')
        self.read_counter = random.randint(2, self.max_pipe_length)

    def predict(self):
        bvalid = 0
        rvalid = 0
        rdata = 0
        if self.write_counter:
            if self.write_counter == 1:
                bvalid = 1
        if self.read_counter:
            if self.read_counter == 1:
                rvalid = 1
        o = make_empty_axi4lite_s2m_dict()
        o['bvalid'] = bvalid
        o['rvalid'] = rvalid
        o['rdata'] = rdata
        return {
            'o': o,
        }
        

    def process(self, inputs):
        if inputs['i']['wvalid']:
            assert(inputs['i']['awvalid'] == 1)
            self.handle_write()
        if inputs['i']['arvalid']:
            self.handle_read()
        bvalid = 0
        rvalid = 0
        rdata = 0
        if self.write_counter:
            if self.write_counter == 1:
                bvalid = 1
            self.write_counter -= 1
        if self.read_counter:
            if self.read_counter == 1:
                rvalid = 1
            self.read_counter -= 1
        o = make_empty_axi4lite_s2m_dict()
        o['bvalid'] = bvalid
        o['rvalid'] = rvalid
        o['rdata'] = rdata
        if inputs['reset']:
            self.reset()
        return {
            'o': o,
        }
            
        
