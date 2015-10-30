import os
import shutil

from pyvivado import builder
from pyvivado.hdl.wrapper import inner_wrapper, file_testbench

def make_directory(interface, directory, data):
    external_dir = os.path.join(directory, 'external')
    if os.path.exists(external_dir):
        raise ValueError('Directory {} already exists.'.format(external_dir))
    sim_dir = os.path.join(external_dir, 'sim')
    synth_dir = os.path.join(external_dir, 'synth')
    os.makedirs(external_dir)
    os.makedirs(sim_dir)
    os.makedirs(synth_dir)
    interface.write_input_file(
        data, os.path.join(sim_dir, 'input.data'))
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
        sim_dir, top_builders=design_builders, top_params=interface.parameters)
    simulation_requirements = builder.build_all(
        sim_dir, top_builders=simulation_builders, top_params=interface.parameters)
    ips = builder.condense_ips(
        design_requirements['ips'] + simulation_requirements['ips'])
    design_files = design_requirements['filenames']
    simulation_files = simulation_requirements['filenames']
    for fn in design_files:
        head, tail = os.path.split(fn)
        shutil.copyfile(fn, os.path.join(synth_dir, tail))
        if head == sim_dir:
            os.remove(fn)
    for fn in simulation_files:
        head, tail = os.path.split(fn)
        if head != sim_dir:
            shutil.copyfile(fn, os.path.join(sim_dir, tail))
            
    
    
