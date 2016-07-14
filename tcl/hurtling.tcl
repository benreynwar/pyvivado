package provide hurtling 0.1

namespace eval ::hurtling {
}

proc ::hurtling::analyze_and_elaborate {design_files top_module} {
    foreach design_file $design_files {
        analyze -format vhdl $design_file
    }
    elaborate $top_module
    link
}

proc ::hurtling::group_paths {} {
     group_path -name OUTPUTS -to [all_outputs]
     group_path -name INPUTS -from [all_inputs]
     group_path -name COMBO -from [all_inputs] -to [all_outputs]
}
