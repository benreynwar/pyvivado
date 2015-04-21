import os
import logging
import math

logger = logging.getLogger(__name__)

from pyvivado import config, utils

def logceil(n):
    if n == 0:
        val = 0
    else:
        val = int(math.ceil(float(math.log(n))/math.log(2)))
    # To keep things simple never return 0.
    # Declaring reg with 0 length is not legal.
    if val == 0:
        val = 1
    return val


class SignalType(object):

    base_type = None

    def __init__(self, name, conversion_name=None):
        self.name = name
        if conversion_name is None:
            conversion_name = name
        self.conversion_name = conversion_name

    def typ(self):
        return self.name

    def defs_and_imps(self):
        defs = ()
        imps = ()
        return (defs, imps)

    def conversion_to_slv(self, v):
        to_slv = '{name}_to_slv({v})'.format(name=self.conversion_name, v=v)
        return to_slv
        
    def conversion_from_slv(self, v):
        from_slv = '{name}_from_slv({v})'.format(name=self.conversion_name, v=v)
        return from_slv


class StdLogic(SignalType):

    def __init__(self):
        self.width = 1
        self.named_type = True
        super().__init__(name='std_logic')

    def conversion_from_slv(self, v):
        from_slv = '{v}(0)'.format(v=v)
        return from_slv

    def to_bitstring(self, value):
        if value in (0, False):
            bit = '0'
        elif value in (1, True):
            bit = '1'
        elif value in (None, ):
            bit = 'X'
        else:
            raise ValueError('StdLogic has unknown value {}'.format(value))
        return bit

    def from_bitstring(self, value):
        if value == '1':
            output = 1
        elif value == '0':
            output = 0
        elif value in ('X', 'U'):
            output = None
        else:
            raise ValueError('StdLogic has unknown value {}'.format(value))
        return output

std_logic_type = StdLogic()


class StdLogicVector(SignalType):

    base_type = 'std_logic_vector'

    def __init__(self, width, name=None):
        self.width = width
        if name is None:
            self.name = self.base_type
            self.named_type = False
        else:
            self.named_type = True
        super().__init__(name=name)

    def typ(self):
        if self.named_type:
            typ = self.name
        else:
            typ = '{}({}-1 downto 0)'.format(self.base_type, self.width)
        return typ

    def defs_and_imps(self):
        if self.named_type:
            defs = ('subtype {} is {}({}-1 downto 0);'.format(
                    self.name, self.base_type, self.width),)
        else:
            defs = ()
        imps = ()
        return (defs, imps)
        
    def conversion_to_slv(self, v):
        return 'std_logic_vector({v})'.format(v=v)

    def conversion_from_slv(self, v):
        return '{base_type}({v})'.format(base_type=self.base_type, v=v)

    def to_bitstring(self, value):
        bits = unsigned_integer_to_std_logic_vector(value, self.width)
        return bits
        
    def from_bitstring(self, bitstring):
        unsigned_int = std_logic_vector_to_unsigned_integer(bitstring)
        return unsigned_int


class Unsigned(StdLogicVector):
    
    base_type = 'unsigned'


unsigned_type = Unsigned('unsigned')


class Signed(StdLogicVector):

    base_type = 'signed'
    
    def to_bitstring(self, value):
        bits = signed_integer_to_std_logic_vector(value, self.width)
        return bits

    def from_bitstring(self, bitstring):
        signed_int = std_logic_vector_to_signed_integer(bitstring)
        return signed_int

signed_type = Signed('signed')


class Integer(SignalType):

    base_type = 'integer'

    def __init__(self, minimum, maximum, name=None):
        if name is None:
            name = self.base_type
            self.named_type = False
        else:
            self.named_type = True
        super().__init__(name)
        self.minimum = minimum
        self.maximum = maximum
        max_mag = max(-minimum, maximum+1)
        self.width = logceil(max_mag) + 1

    def typ(self):
        if self.named_type:
            typ = self.name
        else:
            typ = '{name} range -{minimum} to {maximum}'.format(
                name=self.name, minimum=-self.minimum, maximum=self.maximum)
        return typ

    def defs_and_imps(self):
        if self.named_type:
            defs = (
                'subtype {name} is {base_type} range -{minimum} to {maximum}'
                .format(
                    name=self.name,
                    base_type=self.base_type,
                    minimum = -self.minimum,
                    maximum = self.maximum,),)
        else:
            defs = ()
        imps = ()
        return (defs, imps)

    def conversion_to_slv(self, v):
        return 'std_logic_vector(to_signed({v}, {width}))'.format(
            v=v, width=self.width)

    def conversion_from_slv(self, v):
        return 'to_integer(signed({v}))'.format(v=v)

    def to_bitstring(self, value):
        bits = signed_integer_to_std_logic_vector(value, self.width)
        return bits

    def from_bitstring(self, bitstring):
        signed_int = std_logic_vector_to_signed_integer(bitstring)
        return signed_int


class Natural(Integer):
    
    base_type = 'natural'

    def __init__(self, maximum, name=None):
        super().__init__(minimum=0, maximum=maximum, name=name)


def make_array_defs(contained_type):
    params = {
        'name': contained_type.name,
        'width': contained_type.width,
        'to_slv': contained_type.conversion_to_slv('input(ii)'),
        'from_slv': contained_type.conversion_from_slv('input((ii+1)*W-1 downto ii*W)')
    }
    type_def = '''type array_of_{name} is array(integer range <>) of {name};'''.format(**params)
    to_slv_fn_def = '''function array_of_{name}_to_slv(input: array_of_{name}) return std_logic_vector;'''.format(**params)
    to_slv_fn_imp = '''function array_of_{name}_to_slv(input: array_of_{name}) return std_logic_vector is
  constant W: positive := {width};
  variable output: std_logic_vector((input'HIGH+1)*W-1 downto input'LOW*W);
begin
  for ii in input'range loop
    output((ii+1)*W-1 downto ii*W) := {to_slv};
  end loop;
  return output;
end function;'''.format(**params)
    from_slv_fn_def = '''function array_of_{name}_from_slv(input: std_logic_vector) return array_of_{name};'''.format(**params)
    from_slv_fn_imp = '''function array_of_{name}_from_slv(input: std_logic_vector) return array_of_{name} is
  constant W: positive := {width};
  variable output: array_of_{name}((input'HIGH+1)/W-1 downto input'LOW/W);
begin
  for ii in output'range loop
   output(ii) := {from_slv};
  end loop;
  return output;
end function;'''.format(**params)
    return (
        (type_def, to_slv_fn_def, from_slv_fn_def),
        (to_slv_fn_imp, from_slv_fn_imp),
    )


class Record(SignalType):

    def __init__(self, contained_types, name):
        self.named_type = True
        super().__init__(name=name)
        # Start from type that is positioned in high indices.
        # Which will actually be low indices for the python bitstring.
        self.contained_types = contained_types
        self.width = sum([t[1].width for t in contained_types])
        
    def to_bitstring(self, d):
        contained_names = [t[0] for t in self.contained_types]
        if set(contained_names) != set(d.keys()):
            raise ValueError(
                'Key in dictionary {} do not match names of contained types {}'.format(
                    set(d.keys()), contained_names))
        bitstrings = []
        for name, typ in self.contained_types:
            bitstrings.append(typ.to_bitstring(d[name]))
        return ''.join(bitstrings)

    def from_bitstring(self, bitstring):
        d = {}
        running_width = 0
        for name, typ in self.contained_types:
            width = typ.width
            value = typ.from_bitstring(
                bitstring[running_width: running_width+typ.width])
            d[name] = value
            running_width += width
        return d
            

class Array(SignalType):
    
    def __init__(self, contained_type, size, name=None, conversion_name=None, named_type=True):
        if (name is None) or (not named_type):
            if name is None:
                name = 'array_of_{}'.format(contained_type.name)
            self.named_type = False
        else:
            self.named_type = True
        super().__init__(name=name, conversion_name=conversion_name)
        self.contained_type = contained_type
        self.size = size
        self.width = size * contained_type.width

    def typ(self):
        if self.named_type:
            typ = self.name
        else:
            typ = '{}({}-1 downto 0)'.format(self.name, self.size)
        return typ

    def defs_and_imps(self):
        if self.named_type:
            defs = (
                'subtype {name} is array_of_{contained_type.name}({size}-1 downto 0);'
                .format(
                    name=self.name,
                    contained_type=self.contained_type.name,
                    size=self.size))
        else:
            defs = ()
        imps = ()
        return (defs, imps)

    def to_bitstring(self, list_of_values):
        if len(list_of_values) != self.size:
            error_message = 'Converting array of bitstring. Length of array is {} but we were expecting {}.'.format(
                len(list_of_values), self.size)
            logger.error(error_message)
            raise ValueError(error_message)
        assert(len(list_of_values) == self.size)
        # Index of 0 should go to right of bitstring for consistency.
        bitstrings = []
        for value in reversed(list_of_values):
            bitstrings.append(self.contained_type.to_bitstring(value))
        return ''.join(bitstrings)

    def from_bitstring(self, bitstring):
        values = []
        width = self.contained_type.width
        for i in range(self.size):
            value = self.contained_type.from_bitstring(bitstring[i*width: (i+1)*width])
            values.append(value)
        values.reverse()
        return values


def signed_integer_to_std_logic_vector(i, width):
    '''
    Most significant bit goes to left of string.
    Uses two's complement.
    '''
    if abs(i) >= pow(2, width-1):
        raise ValueError('Cannot convert signed integer {} to std_logic_vector of width {} (not allowing all 1s for safety)'.format(i, width))
    if i < 0:
        i += pow(2, width)
    bits = unsigned_integer_to_std_logic_vector(i, width)
    return bits

def unsigned_integer_to_std_logic_vector(i, width):
    '''
    Most significant bit goes to left of string.
    '''
    if i is None:
        return 'X' * width
    if (i >= pow(2, width)) or (i < 0):
        raise ValueError(
            'Unsigned integer {} cannot be expressed in {} bits'.format(i, width))
    bits = []
    for j in range(width):
        if i % 2 == 0:
            bits.append('0')
        else:
            bits.append('1')
        i = i//2
    bits.reverse()
    return ''.join(bits)

def std_logic_vector_to_unsigned_integer(d):
    value = 1
    output = 0
    for bit in reversed(d):
        if bit == '1':
            output += value
        elif bit != '0':
            output = None
            break
        value *= 2
    return output

def std_logic_vector_to_signed_integer(d):
    i = std_logic_vector_to_unsigned_integer(d)
    if i is not None:
        powered = pow(2, len(d))
        if i >= powered/2:
            i -= powered
    return i

def make_defs_file(filename, package_name, signal_types, contained_signal_types):
    defs = []
    imps = []
    for signal_type in signal_types:
        new_defs, new_imps = signal_type.defs_and_imps()
        defs += new_defs
        imps += new_imps
    for signal_type in contained_signal_types:
        new_defs, new_imps = make_array_defs(signal_type)
        defs += new_defs
        imps += new_imps
    template_fn = os.path.join(config.basedir, 'hdl', 'definitions.vhd.t')
    template_params = {
        'definitions': defs,
        'implementations': imps,
        'package_name': package_name,
    }
    utils.format_file(template_fn, filename, template_params)
    
def sint_to_uint(sint, width):
    sint_signal = Signed(width=width)
    uint_signal = Unsigned(width=width)
    bitstring = sint_signal.to_bitstring(sint)
    uint = uint_signal.from_bitstring(bitstring)
    return uint

def uint_to_sint(sint, width):
    sint_signal = Signed(width=width)
    uint_signal = Unsigned(width=width)
    bitstring = uint_signal.to_bitstring(sint)
    sint = sint_signal.from_bitstring(bitstring)
    return sint

def uint_to_complex(uint, width):
    f = pow(2, width)
    uint_A = uint // f
    uint_B = uint % f
    sint_A = uint_to_sint(uint_A, width)
    sint_B = uint_to_sint(uint_B, width)
    c = complex(sint_B, sint_A)
    return c

def complex_to_uint(c, width):
    uint_A = sint_to_uint(c.imag, width)
    uint_B = sint_to_uint(c.real, width)
    uint = uint_A * pow(2, width) + uint_B
    return uint
    
def list_of_uints_to_uint(list_of_uints, width):
    value_signal = Unsigned(width=width)
    array_signal = Array(value_signal, len(list_of_uints))
    uint_signal = Unsigned(width=len(list_of_uints)*width)
    bitstring = array_signal.to_bitstring(list_of_uints)
    uint = uint_signal.from_bitstring(bitstring)
    return uint

def list_of_sints_to_uint(list_of_sints, width):
    value_signal = Signed(width=width)
    array_signal = Array(value_signal, len(list_of_sints))    
    uint_signal = Unsigned(width=len(list_of_sints)*width)
    bitstring = array_signal.to_bitstring(list_of_sints)
    uint = uint_signal.from_bitstring(bitstring)
    return uint

def uint_to_list_of_sints(uint, size, width):
    value_signal = Signed(width=width)
    array_signal = Array(value_signal, size)    
    uint_signal = Unsigned(width=size*width)
    bitstring = uint_signal.to_bitstring(uint)
    list_of_sints = array_signal.from_bitstring(bitstring)
    return list_of_sints
    
def uint_to_list_of_uints(uint, size, width):
    value_signal = Unsigned(width=width)
    array_signal = Array(value_signal, size)    
    uint_signal = Unsigned(width=size*width)
    bitstring = uint_signal.to_bitstring(uint)
    list_of_sints = array_signal.from_bitstring(bitstring)
    return list_of_sints
    
