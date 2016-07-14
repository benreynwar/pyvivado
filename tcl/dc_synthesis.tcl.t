set design_files {{"{"}} {% for design_file in design_files %}
                   {{design_file}}{% endfor %}
                 {{"}"}}

set top_module {{top_module}}

# Load the design Files.
foreach design_file $design_files {
    analyze -format vhdl $design_file
}
elaborate $top_module
link

# Set timing constraints.
# Not worrying out input and output constraints yet.
reset_design
create_clock -period {{clock_period}} [get_ports clk]
set_clock_uncertainty -setup {{clock_uncertainty}} [get_clocks clk]
set_clock_transition -max {{clock_transition}} [get_clocks clk]

# Compile flow
set_host_options -max_cores 4
# Leave off -spg option for now so that it goes faster.
# Leave off -retime option so that failing timing paths are easier to understand.
compile_ultra
set_app_var verilogout_no_tri true
change_names -rule verilog -hier
write_file -f verilog -hier -out mapped_design.v
write_file -f ddc -hier -out mapped_design.ddc
write_sdc design.sdc
redirect area.rpt { report_area -hier }
redirect power.rpt { report_power -hier }
redirect timing.rpt { report_timing }
exit


