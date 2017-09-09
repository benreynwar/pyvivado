pyvivado
========

A python toolbox for automating vivado projects.

 - Automate generation of Vivado projects.
 - Communicate easily with FPGA-deployed modules from python.

Previously pyvivado contained functionality for generating HDL files
and utilities for testing HDL code with python.  This has now been split
out into separate projects, or abandoned since other open-source tools
were doing it better.

 - Dependency management is best handled using [fusesoc](github.com/olofk/fusesoc).
 - Code generation is split off into [fusesoc_generators](github.com/benreynwar/fusesoc_generators).
 - Testbench generation, and python-based HDL testsing is split off into [slvcodec](github.com/benreynwar/slvcodec).
 - Python tools for Axi4Lite interfaces are split off into [axilent](github.com/benreynwar/axilent).
 - Unit testing of HDL is best handled using [VUnit](github.com/vunit/vunit).
