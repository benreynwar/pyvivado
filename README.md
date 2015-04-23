pyvivado
========

A python toolbox for generation, testing and deployment of Xilinx Vivado projects.

 - Write modules in VHDL or Verilog.
 - Define module dependencies and interfaces using python.
 - Define tests in python.
 - Generate Vivado projects to test modules.
 - Deploy projects to FPGA from python.
 - Communicate with FPGA using python.

Quick Start
-----------
See files [simple\_module.vhd](hdl/test/simple_module.vhd), [simple\_module.py](hdl/test/simple_module.py) and [qa_simple\_module.py](hdl/test/qa_simple_module.py) for examples of what testing with *pyvivado* looks like.

Edit the file [config.py](config.py).
Check that the ``vivado`` variable is pointing at your vivado executable.
Modify ``hwcodes`` so that it contains the hardware codes of the Xilinx devices you have connected.  You can find the hardware codes by looking at the hardware manager in Vivado.

Testing
-------
The idea is that you write your module in Verilog or VHDL like normal, but take advantage of python to make verification less painful.  A separate Vivado project is created for each test case and when the test suite is run projects whose dependencies have been modified are regenerated and the simulations recompiled.  When dependencies are unaltered the projects and simulation executables are not regenerated, however the simulations are still run since the input data may have changed. Running a test suite is still a painfully slow process, but less so.

Because Vivado projects have been created, when encountering an error during testing it is easy to open up the project in a Vivado GUI and take advantage of the debugging tools it offers.

Deployment and Communication
----------------------------
Currently the only supported method of communication between the host computer and the FPGA is through the JTAG-to-AXI Xilinx block.  This is very slow and is not suitable for any application that requires more that afew kB going back and forth.  We have the following items in the communication chain.

 - FPGA design via JTAG-to-AXI block.
 - Vivado process communicating with FPGA via ``create_hw_axi_txn``.
 - [Redis](http://redis.io) acting as an intermediary between the Vivado and python processes.
 - The python process.

This sounds unnecessarily convoluted, and it is!  The use of Redis for example, could be replaced by use of the filesystem, which would be simpler and work much better.

For an example project see [axi\_adder.vhd](hdl/test/axi_adder.vhd) which is a module with an AXI4Lite interface.  It has 4 registers, the first two of which are read/write while the third and fourth are read only.  Reading the third register returns the sum of the first two registers.  The fourth register returns whether the module is in error.

In [axi\_adder.py](hdl/test/axi_adder.py) the ``AxiAdderBuilder`` and ``get_axi_adder_interface`` are defined, along with ``AxiAdderComm``.  ``AxiAdderComm`` is responsible for providing a python interface to the AXI4Lite interface of the module.  In this case, the interface consists of the methods ``add_numbers``, which adds two numbers by writing them to the first two registers and then reading the third, and ``had_error`` which returns a boolean indicating whether the module is in error.

[qa\_axi\_adder.py](hdl/test/qa_axi_adder.py) tests our ``axi_adder`` module both with a HDL simulation and by deploying the module to an FPGA and communicating with the FPGA over JTAG.  A set of commands for the module is generated using the ``AxiAdderComm`` object and these same commands are run on the simulation and on the deployed bitstream.

