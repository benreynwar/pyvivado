pyvivado
========

A python toolbox for generation, testing and deployment of Xilinx
Vivado projects.

 - Write modules in VHDL or Verilog.
 - Define module dependencies and interfaces using python.
 - Define tests in python.
 - Automate generation of Vivado projects.
 - Communicate easily with FPGA-deployed modules from python.

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
even more examples.

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
    
    def __init__(self, params):
        super().__init__(params)
        self.simple_filenames = [
            os.path.join(config.hdldir, 'test', 'simple_module.vhd'),
        ]
```
        
Then create a python function that generates an `interface`.  This is the
information necessary for *pyvivado* to create wrappers for the DUT.

```python
def get_simple_module_interface(params):
    wires_in = (
        ('i_valid', signal.std_logic_type),
        ('i_data', signal.StdLogicVector(width=data_width)),
    )
    wires_out = (
        ('o_valid', signal.std_logic_type),
        ('o_data', signal.StdLogicVector(width=data_width)),
    )
    iface = interface.Interface(
        wires_in, wires_out, module_name='SimpleModule',
        parameters=params, builder=SimpleModuleBuilder({}),
        module_parameters={'DATA_WIDTH': params['data_width']},
	)
    return iface
```

Write tests in Python 
---------------------

Create a new testbench project that reads and writes inputs and outputs
from files.  The DUT is defined by the ``interface`` that is passed in.

```python
p = project.FileTestBenchProject.create_or_update(
    interface=get_simple_module_interface({data_width: 4})
    directory=os.path.abspath('new_project'),
)
```

Define some input data for the DUT.

```python
input_data = []
for i in range(100):
    input_data.append({
        'i_valid': random.randint(0, 1),
        'i_data': random.randint(0, max_data),
    })
```

Run a HDL simulation of the DUT with the specified input data.
*pyvivado* takes care of generating the input file and parsing the output file.

```python  
errors, output_data = p.run_simulation(input_data)
```

We can now confirm that we did not get any errors and that the output data
matched our expectations.  If we find a bug it's easy to open up the project
in the Vivado GUI to see what went wrong.

Deploy using Python
-------------------

Create a project based upon a DUT with an Axi4Lite interface.
The module is wrapped in the Xilinx JTAG-to-AXI block which handles
communication with the host computer (this works fine for low data rates).

```python
p = project.FPGAProject.create_or_update(
    the_builder=axi_adder.AxiAdderBuilder({}),
    parameters={'top_name': 'axi_adder', 'frequency': 100},
    directory=os.path.abspath('proj_testaxiadderfpga'),
)
```

Implement the project, deploy it to the FPGA, and spawn a Vivado process
to communicate with it.

```python
t_impl = p.implement()
t_impl.wait()
t_monitor, conn = p.send_to_fpga_and_monitor()
```

Send AXI commands to the FPGA via the monitoring Vivado process.

```python
conn.write(address=0, data=[1,2])
conn.read(address=0, length=2)
```


