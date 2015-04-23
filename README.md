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

This sounds convoluted, and it is!