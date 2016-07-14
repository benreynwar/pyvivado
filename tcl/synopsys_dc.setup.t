######################################################################
# Logical Library Settings
######################################################################
set_app_var search_path "$search_path {{additional_search_path}}"
set_app_var target_library "{{target_library}}"
set_app_var link_library "* $target_library"
set_app_var symbol_library {{symbol_library}}

######################################################################
# Physical Library Settings
######################################################################

# set_app_var mw_reference_library {{synopsys_libdir}}/mw_lib/sc
# set_app_var mw_design_library {{my_design_library_name}}
# 
# create_mw_lib   -technology {{synopsys_libdir}}/tech/{{tech_name}}.tf \
#                 -mw_reference_library $mw_reference_library \
#                 $mw_design_library
# open_mw_lib     $mw_design_library
# set_tlu_plus_files -max_tluplus {{synopsys_libdir}}/tlup/{{tech_name}}_max.tluplus \
#                    -tech2itf_map {{synopsys_libdir}}/tlup/{{tech_name}}.map

######################################################################
# Load the hurtling tcl library
######################################################################
lappend auto_path {{tcldir}}
package require hurtling
