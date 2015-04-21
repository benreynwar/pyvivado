import asyncio

from pyvivado import signal

module_register = {}

OKAY = 0
EXOKAY = 1
SLVERR = 2
DECERR = 3

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

    
READ_TYPE = 'READ'
WRITE_TYPE = 'WRITE'


class ConnCommandHandler(object):

    def __init__(self, conn):
        self.conn = conn

    def send(self, commands):
        for command in commands:
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
    
    def __init__(self):
        self.unsent_commands = []
        self.sent_commands = []

    def send(self, commands):
        self.unsent_commands += commands

    def make_command_dicts(self):
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
        for command in self.sent_commands:
            results = []
            first_e = None
            for ac in command.axi_commands:
                bad_response = False
                rs = []
                e = None
                for index in range(ac.length):
                    r = None
                    while r is None:
                        if len(ds) == 0:
                            import pdb
                            pdb.set_trace()
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
                        e = Exception('Incorrect number of response.')
                    elif bad_response:
                        e = Exception('Revceived a bad response.')
                    result = None
                else:
                    if bad_response:
                        e = Exception('Revceived a bad response.')
                        result = None
                    else:
                        result = [r[1] for r in rs]
                if first_e is None and e is not None:
                    first_e = e
                results.append(result)
            command.process_response((first_e, results))

class AxiCommand(object):

    def __init__(self, start_address, length, readorwrite, data=None,
                 constant_address=False):
        max_address = pow(2, 32-1)
        self.start_address = start_address
        self.length = length
        self.readorwrite = readorwrite
        self.constant_address = constant_address
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

    def __init__(self):
        self.future = asyncio.Future()

    def process_result(self, result):
        return None, result

    def process_response(self, response):
        e, result = response
        if e is not None:
            self.future.set_exception(e)
        else:
            e, processed_result = self.process_result(result)
            if e is not None:
                self.future.set_exception(e)
            else:
                self.future.set_result(processed_result)

    def set_unsigneds_commands(self, values, address, constant_address=False):
        for value in values:
            assert(value < pow(2, 32))
        command = AxiCommand(
            start_address=address,
            length=len(values),
            readorwrite=WRITE_TYPE,
            data=values,
            constant_address=constant_address,
        )
        return [command]

    def get_unsigneds_commands(self, address, length=1, constant_address=False):
        command = AxiCommand(
            start_address=address,
            length=length,
            readorwrite=READ_TYPE,
            constant_address=constant_address,
        )
        return [command]

    def set_unsigned_commands(self, value, address):
        return self.set_unsigneds_commands(values=[value], address=address)

    def trigger_commands(self, address):
        return self.set_unsigned_commands(0, address)

    def get_unsigned_commands(self, address):
        return self.get_unsigneds_commands(address, length=1)

    def get_boolean_commands(self, address):
        command = AxiCommand(
            start_address=address,
            length=1,
            readorwrite=READ_TYPE)
        return [command]

    def process_get_boolean(self, result):
        e = None
        r = None
        if result == 1:
            r = True
        elif result == 0:
            r = False
        else:
            r = None
            e = Exception('Unknown return value.')
        return e, r

    def set_boolean_commands(self, value, address):
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
        )
        return [command]


class FakeWaitCommand(CommCommand):
    
    def __init__(self, clock_cycles):
        super().__init__()
        self.clock_cycles = clock_cycles
        self.axi_commands = []

class GetBooleanCommand(CommCommand):

    def __init__(self, address):
        super().__init__()
        self.axi_commands = self.get_boolean_commands(address=address)
        
    def process_result(self, result):
        return self.process_get_boolean(result[0][0])

class SetBooleanCommand(CommCommand):

    def __init__(self, value, address):
        super().__init__()
        self.axi_commands = self.set_boolean_commands(value=value, address=address)

class GetUnsignedCommand(CommCommand):

    def __init__(self, address):
        super().__init__()
        self.axi_commands = self.get_unsigned_commands(address=address)

    def process_result(self, result):
        return None, result[0][0]
    
class SetUnsignedCommand(CommCommand):

    def __init__(self, value, address):
        super().__init__()
        self.axi_commands = self.set_unsigned_commands(value=value, address=address)

class SetUnsignedsCommand(CommCommand):

    def __init__(self, values, address, constant_address=False):
        super().__init__()
        self.axi_commands = self.set_unsigneds_commands(
            values=values, address=address, constant_address=constant_address)

class TriggerCommand(CommCommand):
    
    def __init__(self, address):
        super().__init__()
        self.axi_commands = self.trigger_commands(address)


class CombinedCommands(CommCommand):

    def __init__(self, commands):
        super().__init__()
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

    def fake_wait(self, clock_cycles):
        command = FakeWaitCommand(clock_cycles=clock_cycles)
        self.handler.send([command])
        return command.future
    
    def get_boolean(self, address):
        command = GetBooleanCommand(address=address)
        self.handler.send([command])
        return command.future
        
    def set_boolean(self, value, address):
        command = SetBooleanCommand(value=value, address=address)
        self.handler.send([command])
        return command.future

    def get_unsigned(self, address):
        command = GetUnsignedCommand(address=address)
        self.handler.send([command])
        return command.future 

    def set_unsigned(self, value, address):
        command = SetUnsignedCommand(value=value, address=address)
        self.handler.send([command])
        return command.future 

    def set_unsigneds(self, values, address, constant_address=False):
        command = SetUnsignedsCommand(
            values=values, address=address, constant_address=constant_address)
        self.handler.send([command])
        return command.future 

    def trigger(self, address):
        command = TriggerCommand(address=address)
        self.handler.send([command])
        return command.future
       
        
