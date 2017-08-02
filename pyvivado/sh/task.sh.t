#!/usr/bin/env bash

# Update the state of this task to 'RUNNING'.
echo "RUNNING" > current_state.txt
# Run the command
{command}
# Check if it succeeded.
if [ $? -eq 0 ]; then
    echo "FINISHED_OK" > current_state.txt
    echo "FINISHED_OK" > finished.txt
else
    echo "FINISHED_ERROR" > current_state.txt 
    echo "FINISHED_ERROR" > finished.txt 
fi
