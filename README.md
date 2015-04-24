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

Edit the file [config.py](config.py).  Check that the ``vivado``
variable is pointing at your vivado executable.  Modify ``hwcodes`` so
that it contains the hardware codes of the Xilinx devices you have
connected.

Write tests in Python 
---------------------
Writing verification tests in a HDL can be cumbersome.  *pyvivado*
makes it easy to write python unittests that compare the expected
output from a Vivado simulation with the actual output.  The
generation of VHDL wrappers and the creation of the Vivado projects is
automated.  Projects and simulation executables are only updated when
their contents are modified.  When errors are encountered during
testing it is easy to open up the project in a Vivado GUI and take
advantage of the debugging tools it offers.

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
matched our expectations.

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


