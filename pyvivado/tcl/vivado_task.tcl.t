# -*- tcl -*- 

# Update the state of this task to 'RUNNING'.
set current_state_f current_state.txt
set fileId [open $current_state_f "w"]
puts -nonewline $fileId RUNNING
close $fileId
# We also write the state to finished.txt when we finish.
set finished_f finished.txt
# Put our command in a catch so that if we have errors in
# the command, we'll still update the state correctly before
# exiting.
if {{[catch {{
  lappend auto_path {{{tcl_directory}}}
  package require pyvivado
  # And the actual command that this task was created to perform.
  {command}
}} message]}} {{
  # Handle an error in the command.
  puts "ERROR: $message"
  set fileId [open $current_state_f "w"]
  puts -nonewline $fileId FINISHED_ERROR
  close $fileId
  set fileId [open $finished_f "w"]
  puts -nonewline $fileId FINISHED_ERROR
  close $fileId
}} else {{
  # Everything went smoothly so update our state
  # with FINISHED_OK.
  set fileId [open $current_state_f "w"]
  puts -nonewline $fileId FINISHED_OK
  close $fileId
  set fileId [open $finished_f "w"]
  puts -nonewline $fileId FINISHED_OK
  close $fileId
}}
