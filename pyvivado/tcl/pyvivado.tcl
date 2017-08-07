package provide pyvivado 0.1

namespace eval ::pyvivado {
}

# Create a new Vivado project.
# Args:
#     `project_dir`: The directory in which the project will be created.
#     `design_files`: The synthesizable design files (can be "  ").
#     `simulation_files`: The wrapper files for simulation (can be "  ").
#     `part`: The part for which we will implement (can be "").
#     `board`: The board for which we will implement (can be "").
#     `ips`: A list of (ip_name, ip_version, module_name, properties) used
#         define the IP blocks that are required.
#     `top_module`: The top module of the design (can be "").
proc ::pyvivado::create_vivado_project {project_dir design_files simulation_files part board ips top_module} {
    if {$part != ""} {
        create_project TheProject $project_dir -part $part
    } else {
        create_project TheProject $project_dir
    }
    set_property target_language "vhdl" [current_project]
    set_property verilog_define GIT_HASH=AAAA [current_fileset]
    if {$board != ""} {
        set_property board_part $board [current_project]
    }
    if {$design_files != "  "} {
        add_files -fileset sources_1 -norecurse $design_files
    }
    if {$simulation_files != "  "} {
        add_files -fileset sim_1 -norecurse $simulation_files
    }
    foreach ip $ips {
        lassign $ip ip_name ip_version module_name properties
        puts "DEBUG: ip_name = $ip_name"
        puts "DEBUG: ip_version = $ip_version"
        puts "DEBUG: module_name = $module_name"
        if {$ip_version != ""} {
            create_ip -name $ip_name -version $ip_version -vendor xilinx.com -library ip -module_name $module_name
        } else {
            create_ip -name $ip_name -vendor xilinx.com -library ip -module_name $module_name
        }
        foreach property $properties {
            lassign $property property_name property_value
            puts "DEBUG: Setting $property_name = $property_value"
            set_property -name CONFIG.$property_name -value $property_value -objects [get_ips $module_name]
        }
    }
    set_property SOURCE_SET sources_1 [get_filesets sim_1]
    if {$top_module != ""} {
	set_property top $top_module [get_filesets sim_1]
    }
    update_compile_order -fileset sim_1
    update_compile_order -fileset sources_1
}

proc ::pyvivado::does_fileset_exist {simname} {
    set filesets [get_filesets]
    set fileset_exists false
    foreach fileset $filesets {
        if {$fileset == $simname} {
            set fileset_exists true
        }
    }
    return $fileset_exists
}

# Check if the project has been synthesized yet.
proc ::pyvivado::is_synthesized {} {
    set is_done 1
    if {[catch {wait_on_run synth_1} errmsg]} {
        set is_done 0
    }
    return $is_done
}

# Check if the project has been implemented yet.
proc ::pyvivado::is_implemented {} {
    set is_done 1
    if {[catch {wait_on_run impl_1} errmsg]} {
        set is_done 0
    }
    return $is_done
}

# Synthesize the project if it hasn't been yet.
proc ::pyvivado::synthesize {keep_hierarchy} {
    set_property STEPS.SYNTH_DESIGN.ARGS.FLATTEN_HIERARCHY full [get_runs synth_1]
    if {$keep_hierarchy != ""} {
	set_property STEPS.SYNTH_DESIGN.ARGS.FLATTEN_HIERARCHY rebuilt [get_runs synth_1]
    }
    set synthesized [::pyvivado::is_synthesized]
    if {$synthesized == 0} {
        launch_runs synth_1
        wait_on_run synth_1
    }
}

# Implement the project if it hasn't been yet.
proc ::pyvivado::implement {} {
    set implemented [::pyvivado::is_implemented]
    if {$implemented == 0} {
        ::pyvivado::synthesize {}
        launch_runs impl_1 -to_step write_bitstream
        wait_on_run impl_1
    }
}

# Implement the project but skip generating the bitstream.
proc ::pyvivado::implement_without_bitstream {} {
    set implemented [::pyvivado::is_implemented]
    if {$implemented == 0} {
        ::pyvivado::synthesize {}
	set_property STEPS.PHYS_OPT_DESIGN.IS_ENABLED true [get_runs impl_1]
        launch_runs impl_1
        wait_on_run impl_1
    }
}

# Open the project (specified by the `proj_dir`) and sythesize
proc ::pyvivado::open_and_synthesize {proj_dir keep_hierarchy} {
    open_project "${proj_dir}/TheProject.xpr"
    ::pyvivado::synthesize $keep_hierarchy
}

# Open the project (specified by the `proj_dir`) and implement it.
proc ::pyvivado::open_and_implement {proj_dir} {
    open_project "${proj_dir}/TheProject.xpr"
    ::pyvivado::implement
}

proc ::pyvivado::create_simset {proj_dir test_name sim_type simulation_files} {
    set simname "${test_name}_${sim_type}"
    set fileset_exists [::pyvivado::does_fileset_exist $simname]
    if {$fileset_exists} {
        puts "ERROR: Tried to create simulation but directory already existed."
    } else {
        create_fileset -simset $simname
        if {$simulation_files != "  "} {
            puts "DEBUG: adding simulation files = '${simulation_files}'"
            add_files -fileset $simname -norecurse $simulation_files
        } else {
            puts "DEBUG: no simulation files."
        }
        set_property generic "DATAINFILENAME=${proj_dir}/${test_name}/input.data DATAOUTFILENAME=${proj_dir}/${test_name}/vivado_${sim_type}_output.data" [get_filesets $simname]
    }
}
    
# Run a behavioral HDL simulation.
proc ::pyvivado::run_hdl_simulation {proj_dir test_name runtime simulation_files} {
    set simname "${test_name}_hdl"
    set fileset_exists [::pyvivado::does_fileset_exist $simname]
    if {! $fileset_exists} {
        ::pyvivado::create_simset ${proj_dir}/.. $test_name hdl $simulation_files
    }
    set sim_dir "${proj_dir}/TheProject.sim/${simname}/behav"
    set sim_dir_exists [file isdirectory $sim_dir]
    if {$sim_dir_exists == 1} {
        set_property skip_compilation 1 [get_filesets $simname]
        puts "DEBUG: Skipping test compilation."
    } else {
        set_property skip_compilation 0 [get_filesets $simname]
        puts "DEBUG: Not skipping test compilation."
    }
    set_property top FileTestBench [get_filesets $simname]
    set_property xsim.simulate.runtime $runtime [get_filesets $simname]
    puts "DEBUG: About to run_hdl_simulation and pwd is [pwd]"
    launch_simulation -simset $simname -mode behavioral
}

# Run a post-synthesis behavioral simulation.
proc ::pyvivado::run_post_synthesis_simulation {proj_dir test_name runtime simulation_files} {
    set simname "${test_name}_post_synthesis"
    set fileset_exists [::pyvivado::does_fileset_exist $simname]
    if {! $fileset_exists} {
        ::pyvivado::create_simset ${proj_dir}/.. $test_name post_synthesis $simulation_files
    }
    set sim_dir "${proj_dir}/TheProject.sim/${simname}/synth"
    set sim_dir_exists [file isdirectory $sim_dir]
    set_property STEPS.SYNTH_DESIGN.ARGS.FLATTEN_HIERARCHY none [get_runs synth_1]
    ::pyvivado::synthesize {}
    set sim_dir "${proj_dir}/TheProject.sim/${simname}/synth"
    set sim_dir_exists [file isdirectory $sim_dir]
    if {$sim_dir_exists == 1} {
        set_property skip_compilation 1 [get_filesets ${simname}]
        puts "DEBUG: Skipping test compilation."
    } else {
        set_property skip_compilation 0 [get_filesets ${simname}]
        puts "DEBUG: Not skipping test compilation."
    }
    set_property top FileTestBench [get_filesets $simname]
    set_property xsim.simulate.runtime $runtime [get_filesets ${simname}]
    puts "DEBUG: About to run_post_synthesis_simulation and pwd is [pwd]"
    launch_simulation -simset ${simname} -mode post-synthesis -type functional
}

# Run a post-implementation timing simulation.
proc ::pyvivado::run_timing_simulation {proj_dir test_name runtime simulation_files} {
    set simname "${test_name}_timing"
    set fileset_exists [::pyvivado::does_fileset_exist $simname]
    if {! $fileset_exists} {
        ::pyvivado::create_simset ${proj_dir}/.. $test_name timing $simulation_files
    }
    set sim_dir "${proj_dir}/TheProject.sim/${simname}/synth"
    set sim_dir_exists [file isdirectory $sim_dir]

    ::pyvivado::implement_without_bitstream
    if {$sim_dir_exists == 1} {
        set_property skip_compilation 1 [get_filesets $simname]
        puts "DEBUG: Skipping test compilation."
    } else {
        set_property skip_compilation 0 [get_filesets $simname]
        puts "DEBUG: Not skipping test compilation."
    }
    set_property xsim.simulate.runtime $runtime [get_filesets $simname]
    puts "DEBUG: About to run_timing_simulation and pwd is [pwd]"
    launch_simulation -simset $simname -mode post-implementation -type timing
}

# Deploy the bitstream to an FPGA and start monitoring it.
# Args:
#     `proj_dir`: The directory where the project we want to deploy is.
#     `hwcode`: The hardware code of the FPGA we want to deploy it to.
#     `fake`: If fake == 1 that we don't deploy it we just pretend we 
#          did any just return 0 for all AXI read commands.
proc ::pyvivado::send_to_fpga_and_monitor {proj_dir hwcode hwtarget jtagfreq fake} {
    if {$fake == 0} {
  open_hw
	connect_hw_server -url localhost:3121
	current_hw_target [get_hw_targets $hwtarget]
	set_property PARAM.FREQUENCY $jtagfreq [get_hw_targets $hwtarget]
	open_hw_target
    }
    ::pyvivado::send_bitstream_to_fpga $proj_dir $hwcode $fake
    ::pyvivado::monitor_redis_inner $hwcode $fake
}

# Monitor REDIS for AXI commands to send to the FPGA.
# Assumes connection with hardware server is already setup.x
proc ::pyvivado::monitor_redis_inner {hwcode fake} {
    package require redis
    set r [redis 127.0.0.1 6379]
    set finish 0
    $r set ${hwcode}_kill 0
    while {$finish == 0} {
        ::pyvivado::check_redis $r $hwcode $fake
        after 100
	set finish [$r get ${hwcode}_kill]
    }
}

# Monitor REDIS for AXI commands to send to the FPGA.
proc ::pyvivado::monitor_redis {hwcode hwtarget jtagfreq fake} {
    if {$fake == 0} {
	connect_hw_server -host localhost -port 60001 -url localhost:3121
	current_hw_target [get_hw_targets $hwtarget]
	set_property PARAM.FREQUENCY $jtagfreq [get_hw_targets $hwtarget]
	open_hw_target
	current_hw_device [lindex [get_hw_devices] 0]
	refresh_hw_device [lindex [get_hw_devices] 0]
    }
    monitor_redis_inner $hwcode $fake
 }

# Send the projects bitstream to the FPGA.
proc ::pyvivado::send_bitstream_to_fpga {proj_dir hwcode fake} {
    set bitstreams [glob "${proj_dir}/TheProject.runs/impl_1/*.bit"]
    set bitstream [lindex $bitstreams 0]
    if {$fake == 0} {
	set_property PROGRAM.FILE $bitstream [lindex [get_hw_devices] 0]
	set_property PROBES.FILE "${proj_dir}/TheProject.runs/impl_1/debug_nets.ltx" [lindex [get_hw_devices] 0]
	current_hw_device [lindex [get_hw_devices] 0]
	refresh_hw_device [lindex [get_hw_devices] 0]
	program_hw_devices [lindex [get_hw_devices] 0]
	refresh_hw_device [lindex [get_hw_devices] 0]
    }
    # Make a note that this hardware is now running this project.
    package require redis
    set r [redis 127.0.0.1 6379]
    $r set ${hwcode}_projdir $proj_dir
}

# Check redis for any AXI commands to send to the FPGA.
# Writes responses back to redis.
proc ::pyvivado::check_redis {r hwcode fake} {
    puts "checking redis"
    $r set ${hwcode}_last_A [clock format [clock seconds] -format %Y%m%d%H%M%S]
    set output [$r get ${hwcode}_comm]
    set bits [split $output]
    if {[lindex $bits 0] == "C"} {
        set typ [lindex $bits 1]
        set address [lindex $bits 2]
        set data_length [lindex $bits 3]
        if {$typ == "W"} {
            puts "writing to axi"
            set response "R W $address"
            for {set i 0} {$i < $data_length} {incr i} {
                if {$fake == 0} {
                    set results [::pyvivado::write_axi [format %08x [expr {$address+$i}]] [format %08x [lindex $bits [expr {4+$i}]]]]
                    set response "$response [lindex $results 1]"
                } else {
                    # Don't think the response really matter for write.
                    set response "$response 0"
                }
	             	$r set ${hwcode}_last_A [clock format [clock seconds] -format %Y%m%d%H%M%S]
            }
            $r set ${hwcode}_comm $response
        }
        if {$typ == "R"} {
            puts "reading from axi length is $data_length"
            set response "R R $address"
	          for {set i 0} {$i < $data_length} {incr i} {
		            if {$fake == 0} {
	            	    set results [::pyvivado::read_axi [format %08x [expr {$address+$i}]]]
	            	    set response "$response [lindex $results 1]"
            		} else {
		                set response "$response 0"
                }
                if {$i % 100 == 0} {
		                puts $i
		                $r set ${hwcode}_last_A [clock format [clock seconds] -format %Y%m%d%H%M%S]
	              }
	          }
            $r set ${hwcode}_comm $response
        }
	      if {$typ == "WW"} {
            puts "writing to axi repeatedly"
            set response "R WW $address"
            for {set i 0} {$i < $data_length} {incr i} {
	              if {$fake == 0} {
		                set results [::pyvivado::write_axi [format %08x [expr {$address}]] [format %08x [lindex $bits [expr {4+$i}]]]]
		                set response "$response [lindex $results 1]"
		            } else {
		                set response "$response 0"
		            }
		            $r set ${hwcode}_last_A [clock format [clock seconds] -format %Y%m%d%H%M%S]
            }
            $r set ${hwcode}_comm $response
        }         
	      if {$typ == "RR"} {
            puts "reading from axi repeatedly"
            set response "R RR $address"
            for {set i 0} {$i < $data_length} {incr i} {
		            if {$fake == 0} {
	            	    set results [::pyvivado::read_axi [format %08x [expr {$address}]]]
	            	    set response "$response [lindex $results 1]"
            		} else {
		                set response "$response 0"
                }
                if {$i % 100 == 0} {
		                puts $i
		                $r set ${hwcode}_last_A [clock format [clock seconds] -format %Y%m%d%H%M%S]
	              }
            }
            $r set ${hwcode}_comm $response
        }
    }
}

# Send an AXI read command to the FPGA.
proc ::pyvivado::read_axi {address} {
    create_hw_axi_txn read_txn [get_hw_axis hw_axi_1] -type READ -address $address -len 1
    run_hw_axi [get_hw_axi_txns read_txn]
    set results [report_hw_axi_txn [get_hw_axi_txns read_txn]]
    delete_hw_axi_txn [get_hw_axi_txns read_txn]
    return $results
}

# Send an AXI write command to the FPGA.
proc ::pyvivado::write_axi {address value} {
    create_hw_axi_txn write_txn [get_hw_axis hw_axi_1] -type WRITE -address $address -len 1 -data $value
    run_hw_axi [get_hw_axi_txns write_txn]
    set results [report_hw_axi_txn [get_hw_axi_txns write_txn]]
    delete_hw_axi_txn [get_hw_axi_txns write_txn]
    return $results
}

proc ::pyvivado::generate_impl_reports {proj_dir} {
    open_project "${proj_dir}/TheProject.xpr"
    open_run impl_1
    report_power -file ${proj_dir}/impl_power.txt
    report_utilization -file ${proj_dir}/impl_utilization.txt -hierarchical -hierarchical_depth 10
}

proc ::pyvivado::generate_synth_reports {proj_dir} {
    open_project "${proj_dir}/TheProject.xpr"
    open_run synth_1
    report_power -file ${proj_dir}/synth_power.txt
    report_utilization -file ${proj_dir}/synth_utilization.txt -hierarchical -hierarchical_depth 10
}
