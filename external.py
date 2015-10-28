import os
import shutil

from pyvivado import builder
from pyvivado.hdl.wrapper import inner_wrapper, file_testbench

def make_directory(interface, directory):
    if os.path.exists(directory):
        raise ValueError('Directory {} already exists.'.format(directory))
    os.makedirs(directory)
    inner_wrapper_builder = inner_wrapper.InnerWrapperBuilder({
        'interface': interface,
    })
    file_testbench_builder = file_testbench.FileTestbenchBuilder({
        'interface': interface,
    })
    interface.parameters['factory_name'] = interface.factory_name
    design_builders = [inner_wrapper_builder, interface.builder]
    simulation_builders = [file_testbench_builder,]
    design_requirements = builder.build_all(
        directory, top_builders=design_builders, top_params=interface.parameters)
    simulation_requirements = builder.build_all(
        directory, top_builders=simulation_builders, top_params=interface.parameters)
    ips = builder.condense_ips(
        design_requirements['ips'] + simulation_requirements['ips'])
    design_files = design_requirements['filenames']
    simulation_files = simulation_requirements['filenames']
    all_files = design_files | simulation_files
    for fn in all_files:
        head, tail = os.path.split(fn)
        if head != directory:
            shutil.copyfile(fn, os.path.join(directory, tail))
            
    
    
