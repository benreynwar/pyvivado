pyvivado
========

A python toolbox for generation, testing and deployment of Xilinx
Vivado projects.

 - Write modules in VHDL or Verilog.
 - Define module dependencies and interfaces using python.
 - Define tests in python.
 - Automate generation of Vivado projects.
 - Communicate easily with FPGA-deployed modules from python.

Warning
-------
I am actively using this myself for projects (as of September 2016), but I'm
not doing a very good job of making sure all the tests and
documentation are up to date, or keeping the API constant.  If you're
thinking of using this for a real project let me know so I know
somebody else is using it and can start being more careful.

Quick Start
-----------

See files [simple\_module.vhd](hdl/test/simple_module.vhd),
[simple\_module.py](hdl/test/simple_module.py) and
[qa_simple\_module.py](hdl/test/qa_simple_module.py) for examples of
what using *pyvivado* looks like.

See files [axi\_adder.vhd](hdl/test/axi_adder.vhd),
[axi\_adder.py](hdl/test/axi_adder.py) and
[qa_axi\_adder.py](hdl/test/qa_axi_adder.py) for a more complex example.

See [github.com/benreynwar/rfgnocchi](https://github.com/benreynwar/rfgnocchi) for
even more examples. (This is now pretty out of date)

Edit the file [config.py](config.py).  Check that the ``vivado``
variable is pointing at your vivado executable.  Modify ``hwcodes`` so
that it contains the hardware codes of the Xilinx devices you have
connected.

Creating a New Module
---------------------

Define the module using VHDL or Verilog just like normal.  In this
example we have two wires passing straight through the module.

```vhdl
library ieee;
use ieee.std_logic_1164.all;

entity SimpleModule is
  generic (
    DATA_WIDTH: positive
    );
  port (
    i_valid: in std_logic;
    i_data: in std_logic_vector(DATA_WIDTH-1 downto 0);
    o_valid: out std_logic;
    o_data: out std_logic_vector(DATA_WIDTH-1 downto 0)
    );
end SimpleModule;

architecture arch of SimpleModule is
begin
  o_valid <= i_valid;
  o_data <= i_data;
end arch;
```

Then create a python object that can generate or specify the required
files and IP (in this case it's pretty simple).

```python
class SimpleModuleBuilder(builder.Builder):

    def __init__(self, params, top_params={}):
        super().__init__(params)
        self.simple_filenames = [
            os.path.join(config.hdldir, 'test', 'simple_module.vhd'),
        ]
```
        
Then create a python function that generates an `interface`.  This is the
information necessary for *pyvivado* to create wrappers for the DUT.

```python
@interface.register('SimpleModule')
def get_simple_module_interface(params):
    '''
    Creates an interface object that is used to generate the verification
    wrappers.
    '''
    module_name = 'SimpleModule'
    data_width = params['data_width']
    builder = SimpleModuleBuilder({}, params)
    module_parameters = {
        'DATA_WIDTH': data_width,
    }
    wires_in = (
        ('i_valid', signal.std_logic_type),
        ('i_data', signal.StdLogicVector(width=data_width)),
    )
    wires_out = (
        ('o_valid', signal.std_logic_type),
        ('o_data', signal.StdLogicVector(width=data_width)),
    )
    iface = interface.Interface(
        wires_in, wires_out, module_name=module_name,
        parameters=params, module_parameters=module_parameters,
        builder=builder)
    return iface
```

Write tests in Python 
---------------------

Write a python class that defines the inputs to send to the DUT and
checks that the outputs are as expected.

```python
class TestSimple():

    def __init__(self, params, n_data=100):
        self.data_width = params['data_width']
        self.n_data = n_data
        self.max_data = pow(2, self.data_width)-1

    def make_input_data(self):
        n_data = 1000
        input_data = [{
          'i_valid': random.randint(0, 1),
          'i_data': random.randint(0, self.max_data),
          } for i in range(n_data)]
        return input_data

    def check_output_data(self, input_data, output_data, pause):
        # This module is really simple and the outputs should just be the
        # same as the inputs.
        input_valids = [d['i_valid'] for d in input_data]
        output_valids = [d['o_valid'] for d in output_data]
        input_data = [d['i_data'] for d in input_data]
        output_data = [d['o_data'] for d in output_data]
        if (input_valids != output_valids) and pause:
            import pdb
            pdb.set_trace()
        assert(input_valids == output_valids)
        if (input_data != output_data) and pause:
            import pdb
            pdb.set_trace()
        assert(input_data == output_data)
```

Run a simulation.  *pyvivado* takes care of creating a vivado project, generating
the stimulus file for the simulation and parsing the output file, so that it can
be validated in python.

```python
from pyvivado import test_utils, config, test_info

@pytest.mark.parametrize('data_width', (1, 2, 7))
@pytest.mark.parametrize('sim_type', test_info.test_sim_types)
def test_simple_module(data_width, sim_type, pause=False):
    '''
    Tests that the inputs are passing straight through SimpleModule
    as expected.
    '''
    directory = os.path.join(config.testdir, 'test',
                             'proj_simplemodule_{}'.format(data_width))
    params = {
        'data_width': data_width,
        'factory_name': 'SimpleModule'
    }
    # Run the simulation and check that the output is correct.
    test_utils.simulate_and_test(
        params=params,
        directory=directory,
        tests=[SimpleTest(params=params, n_data=1000)],
        reset_input={'i_valid': 0, 'i_data': 0},
        sim_type=sim_type,
    )

if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_simple_module(data_width=4, sim_type='vivado_hdl')
```

Deploy using Python
-------------------

Create a project based upon a DUT with an Axi4Lite interface.
The module is wrapped in the Xilinx JTAG-to-AXI block which handles
communication with the host computer (this works fine for low data rates).

```python
params = {
    'top_name': 'axi_adder',
    'frequency': 100,
    }

p = fpga_project.FPGAProject(
    parameters=params,
    directory=os.path.abspath('my_axiadder_directory'),
    board='xilinx:vc709',
    overwrite_ok=True,
)
v = vivado_project.VivadoProject(
    project=p, board='xilinx:vc709', wait_for_creation=True, overwrite_ok=True,
    )
```

Implement the project, deploy it to the FPGA, and spawn a Vivado process
to communicate with it.

```python
t_impl = v.implement()
t_impl.wait()
t_monitor, conn = v.send_to_fpga_and_monitor()
```

Send AXI commands to the FPGA via the monitoring Vivado process.

```python
conn.write(address=0, data=[1,2])
conn.read(address=0, length=2)
```

Disclaimer
----------

This is basically a collection of utilities that I've written to speed
up my HDL development (which I'm pretty new to).  There are almost
certainly still hardcoded tweaks in here that are specific to my use
cases and the boards I'm using.  I would like to make it more
generally useful, but for now, there will almost certainly be some
pain to start off with.  Please let me know of problems you run into!
