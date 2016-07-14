#!/usr/bin/env bash

# First analyze the design files.
{% if vlog_design_files %}
vlogan {% for design_file in vlog_design_files %}{{design_file}} {% endfor %}
if [ $? -ne 0 ]; then
  echo "ERROR: Failure running vlogan. Testing."
  exit 1
fi
{% endif %}
{% if vhdl_design_files %}
vhdlan {% for design_file in vhdl_design_files %}{{design_file}} {% endfor %}
if [ $? -ne 0 ]; then
  echo "ERROR: Failure running vhdlan. Testing."
  exit 1
fi
{% endif %}
vhdlan {% for simulation_file in simulation_files %}{{simulation_file}} {% endfor %}
if [ $? -ne 0 ]; then
  echo "ERROR: Failure running vhdlan. Testing."
  exit 1
fi

# Create the simulation executable.
vcs FileTestBenchWrapped -debug_all
if [ $? -ne 0 ]; then
  echo "ERROR: Failure running VCS compilation."
  exit 1
fi

# And run it
./simv -ucli -f {{tcldir}}simv_post_synthesis.tcl
if [ $? -ne 0 ]; then
  echo "ERROR: Failure running simulation executable ."
  exit 1
fi

exit 0
