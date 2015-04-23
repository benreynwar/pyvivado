package provide pyvivado 0.1

namespace eval ::pyvivado {
    namespace export create_project
}

proc ::pyvivado::create_vivado_project {project_dir design_files simulation_files part board ips top_module} {
    puts $design_files
    puts $simulation_files
    if {$part != ""} {
        create_project TheProject $project_dir -part $part
    } else {
        create_project TheProject $project_dir
    }
    set_property target_language "vhdl" [current_project]
    if {$board != ""} {
        set_property board_part $board [current_project]
    }
    if {$design_files != "  "} {
        add_files -fileset sources_1 -norecurse $design_files
    }
    if {$simulation_files != "  "} {
	puts "DEBUG: adding simulation files = '${simulation_files}'"
        add_files -fileset sim_1 -norecurse $simulation_files
    } else {
	puts "DEBUG: no simulation files."
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

# This is just here for testing tasks
# It never returns and must be killed.
proc ::pyvivado::loop_forever {dummy_file} {
    set counter 0
    while 1 {
	set fileId [open $dummy_file "a"]
	puts $fileId $counter
	close $fileId	
	incr counter
	after 1000
    }
}

proc ::pyvivado::is_synthesized {} {
    set is_done 1
    if {[catch {wait_on_run synth_1} errmsg]} {
        set is_done 0
    }
    return $is_done
}

proc ::pyvivado::is_implemented {} {
    set is_done 1
    if {[catch {wait_on_run impl_1} errmsg]} {
        set is_done 0
    }
    return $is_done
}

proc ::pyvivado::synthesize {} {
    set synthesized [::pyvivado::is_synthesized]
    if {$synthesized == 0} {
        launch_runs synth_1
        wait_on_run synth_1
    }
}

proc ::pyvivado::implement {} {
    set implemented [::pyvivado::is_implemented]
    if {$implemented == 0} {
        ::pyvivado::synthesize
        launch_runs impl_1 -to_step write_bitstream
        wait_on_run impl_1
    }
}

proc ::pyvivado::implement_without_bitstream {} {
    set implemented [::pyvivado::is_implemented]
    if {$implemented == 0} {
        ::pyvivado::synthesize
        launch_runs impl_1
        wait_on_run impl_1
    }
}

proc ::pyvivado::open_and_implement {proj_dir} {
    open_project "${proj_dir}/TheProject.xpr"
    ::pyvivado::implement
}

proc ::pyvivado::run_hdl_simulation {proj_dir runtime} {
    set sim_dir "${proj_dir}/TheProject.sim/sim_1/behav"
    set sim_dir_exists [file isdirectory $sim_dir]
    if {$sim_dir_exists == 1} {
	set_property skip_compilation 1 [get_filesets sim_1]
	puts "DEBUG: Skipping test compilation."
    } else {
	set_property skip_compilation 0 [get_filesets sim_1]
	puts "DEBUG: Not skipping test compilation."
    }
    set_property xsim.simulate.runtime $runtime [get_filesets sim_1]
    puts "DEBUG: About to run_hdl_simulation and pwd is [pwd]"
    launch_simulation -simset sim_1 -mode behavioral
}



proc ::pyvivado::run_post_synthesis_simulation {proj_dir runtime} {
    set_property STEPS.SYNTH_DESIGN.ARGS.FLATTEN_HIERARCHY none [get_runs synth_1]
    ::pyvivado::synthesize
    set sim_dir "${proj_dir}/TheProject.sim/sim_1/synth"
    set sim_dir_exists [file isdirectory $sim_dir]
    if {$sim_dir_exists == 1} {
	set_property skip_compilation 1 [get_filesets sim_1]
	puts "DEBUG: Skipping test compilation."
    } else {
	set_property skip_compilation 0 [get_filesets sim_1]
	puts "DEBUG: Not skipping test compilation."
    }
    set_property xsim.simulate.runtime $runtime [get_filesets sim_1]
    puts "DEBUG: About to run_post_synthesis_simulation and pwd is [pwd]"
    launch_simulation -simset sim_1 -mode post-synthesis -type functional
}

proc ::pyvivado::run_timing_simulation {proj_dir runtime} {
    ::pyvivado::implement_without_bitstream
    set sim_dir "${proj_dir}/TheProject.sim/sim_1/impl"
    set sim_dir_exists [file isdirectory $sim_dir]
    if {$sim_dir_exists == 1} {
	set_property skip_compilation 1 [get_filesets sim_1]
	puts "DEBUG: Skipping test compilation."
    } else {
	set_property skip_compilation 0 [get_filesets sim_1]
	puts "DEBUG: Not skipping test compilation."
    }
    set_property xsim.simulate.runtime $runtime [get_filesets sim_1]
    puts "DEBUG: About to run_timing_simulation and pwd is [pwd]"
    launch_simulation -simset sim_1 -mode post-implementation -type timing
}

proc ::pyvivado::send_to_fpga_and_monitor {proj_dir hwcode fake} {
    ::pyvivado::send_bitstream_to_fpga $proj_dir $hwcode $fake
    ::pyvivado::monitor_redis $hwcode $fake
}

proc ::pyvivado::monitor_redis {hwcode fake} {
    if {$fake == 0} {
	reset_hw_axi [get_hw_axis hw_axi_1]
    }
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

proc ::pyvivado::send_bitstream_to_fpga {proj_dir hwcode fake} {
    puts "DEBUG: proj dir is"
    puts "DEBUG: $proj_dir"
    if {$fake == 0} {
	connect_hw_server -host localhost -port 60001 -url localhost:3121
	current_hw_target [get_hw_targets */xilinx_tcf/Digilent/$hwcode]
	set_property PARAM.FREQUENCY 15000000 [get_hw_targets */xilinx_tcf/Digilent/$hwcode]
	open_hw_target
	set_property PROGRAM.FILE "${proj_dir}/TheProject.runs/impl_1/FileTestBench.bit" [lindex [get_hw_devices] 0]
	set_property PROBES.FILE "${proj_dir}/TheProject.runs/impl_1/debug_nets.ltx" [lindex [get_hw_devices] 0]
	current_hw_device [lindex [get_hw_devices] 0]
	refresh_hw_device [lindex [get_hw_devices] 0]
	program_hw_devices [lindex [get_hw_devices] 0]
	refresh_hw_device [lindex [get_hw_devices] 0]
    }
    package require redis
    set r [redis 127.0.0.1 6379]
    $r set ${hwcode}_projdir $proj_dir
}

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
    }
}

proc ::pyvivado::read_axi {address} {
    create_hw_axi_txn read_txn [get_hw_axis hw_axi_1] -type READ -address $address -len 1
    run_hw_axi [get_hw_axi_txns read_txn]
    set results [report_hw_axi_txn [get_hw_axi_txns read_txn]]
    delete_hw_axi_txn [get_hw_axi_txns read_txn]
    return $results
}

proc ::pyvivado::write_axi {address value} {
    create_hw_axi_txn write_txn [get_hw_axis hw_axi_1] -type WRITE -address $address -len 1 -data $value
    run_hw_axi [get_hw_axi_txns write_txn]
    set results [report_hw_axi_txn [get_hw_axi_txns write_txn]]
    delete_hw_axi_txn [get_hw_axi_txns write_txn]
    return $results
}

