import os
import logging
import hashlib
import shutil

from pyvivado import utils, builder
from pyvivado import hash_helper, params_helper

logger = logging.getLogger(__name__)


def get_hash(files_and_ip):
    '''
    Generate a hash that based on the files and IP in the project.
    This is used to tell when the files in the project have been changed.
    '''
    h = hashlib.sha1()
    design_files = sorted(list(files_and_ip['design_files']))
    simulation_files = sorted(list(files_and_ip['simulation_files']))
    # Sort IPs by their name.
    def get_name(a):
        return a[2]
    ips = sorted(list(files_and_ip['ips']), key=get_name)
    # Check that names are unique
    names = [a[2] for a in ips]
    assert(len(names) == len(set(names)))
    design_files_hash = utils.files_hash(design_files)
    simulation_files_hash = utils.files_hash(simulation_files)
    # FIXME: Not sure whether this will work properly for
    # the ips
    ips_hash = str(tuple(ips)).encode('ascii')
    h.update(utils.files_hash(design_files))
    h.update(utils.files_hash(simulation_files))
    h.update(ips_hash)
    logger.debug('design {} simulation {} ips {}'.format(
        design_files_hash, simulation_files_hash, ips_hash))
    return h.digest()


def get_hash_from_builders(
        directory, design_builders, simulation_builders, parameters,
        top_module, temp_directory=None):
    '''
    Get the project hash for the project that these builders would create.

    We work out the always work out the hash in a dummy directory so we
    don't overwrite things unnecessarily.  Always use dummy directory since
    hash may depend on the directory.
    '''
    if temp_directory is None:
        temp_directory = os.path.join(directory, 'hash_check')
    # Make a new directory for temporary files.
    if os.path.exists(temp_directory):
        shutil.rmtree(temp_directory)
    os.mkdir(temp_directory)
    files_and_ip = make_files_and_ip(
        directory=temp_directory,
        design_builders=design_builders,
        simulation_builders=simulation_builders,
        top_module=top_module,
        parameters=parameters
        )
    # And generate the hash.
    new_hash = get_hash(files_and_ip)
    return new_hash


def make_files_and_ip(
        directory, design_builders, simulation_builders, parameters,
        top_module, exclude_fn=None):
    design_requirements = builder.build_all(
        directory, top_builders=design_builders, top_params=parameters,
        exclude_fn=exclude_fn)
    simulation_requirements = builder.build_all(
        directory, top_builders=simulation_builders, top_params=parameters,
        exclude_fn=exclude_fn)
    ips = builder.condense_ips(
        design_requirements['ips'] + simulation_requirements['ips'])
    files_and_ip = {
        'design_files': design_requirements['filenames'],
        'simulation_files': simulation_requirements['filenames'],
        'ips': ips,
        'top_module': top_module,
        }
    return files_and_ip


class BaseProject(object):
    '''
    The base class for a HDL project.
    '''

    def __init__(self, directory, files_and_ip=None, overwrite_ok=False):
        '''
        Create a python wrapper around a project.

        Args:
           `directory`: Location of the project.
        '''
        self.directory = os.path.abspath(directory)
        if not os.path.exists(directory):
            os.mkdir(directory)
        self.hash_helper = hash_helper.HashHelper(
            self.directory, self.get_hash)
        self.file_helper = params_helper.FilesHelper(self.directory)
        if files_and_ip is not None:
            old_files_and_ip = self.file_helper.read()
            if old_files_and_ip is not None:
                if self.file_helper.has_changed(files_and_ip):
                    if not overwrite_ok:
                        raise Exception('Project has changed. Cannot overwrite.')
                    else:
                        self.file_helper.write(self.files_and_ip, overwrite_ok=True)
            else:
                self.file_helper.write(files_and_ip)
        else:
            files_and_ip = self.file_helper.read()
        self.files_and_ip = files_and_ip
        if self.hash_helper.is_changed():
            if not overwrite_ok:
                raise Exception('Project has changed.  Cannot overwrite.')
        if self.files_and_ip is None:
            raise Exception('No Files and IP specified')
        self.hash_helper.write()

    def get_hash(self):
        return get_hash(self.files_and_ip)

    def copy_files(self, directory):
        # The synth and sim directories should not exist yet.
        synth_dir = os.path.join(directory, 'synth')
        sim_dir = os.path.join(directory, 'sim')
        assert(os.path.exists(synth_dir, False))
        assert(os.path.exists(sim_dir, False))
        os.mkdir(synth_dir)
        os.mkdir(sim_dir)
        for fn in self.files_and_ip['design_files']:
            head, tail = os.path.split(fn)
            shutil.copyfile(fn, os.path.join(synth_dir, tail))
        for fn in self.files_and_ip['simulation_files']:
            head, tail = os.path.split(fn)
            shutil.copyfile(fn, os.path.join(sim_dir, tail))


class BuilderProject(BaseProject):
    '''
    A wrapper around a project.  It assumes that the project was
    created using `Builder`s rather than by explicitly listing the files.
    '''

    def __init__(
            self, directory, design_builders=None, simulation_builders=None,
            parameters=None, top_module=None, overwrite_ok=False,
            exclude_fn=None, additional_files=[]):
        params_fn = os.path.join(directory, 'params.txt')
        self.params_helper = params_helper.ParamsHelper(params_fn)
        if not os.path.exists(directory):
            os.mkdir(directory)
            old_params = None
        else:
            old_params = self.params_helper.read()
            assert(old_params is not None)
        if design_builders is not None:
            parameters['design_builders'] = [b._id() for b in design_builders]
        if simulation_builders is not None:
            parameters['simulation_builders'] = [b._id() for b in simulation_builders]
        if top_module is not None:
            parameters['top_module'] = top_module
        if (old_params is not None):
            if (parameters is not None) and self.params_helper.has_changed(parameters):
                import pdb
                pdb.set_trace()
                raise Exception('Parameters do not match saved values')
            files_and_ip = None
            design_builder_ids = old_params['design_builders']
            simulation_builder_ids = old_params['simulation_builders']
            self.design_builders = [
                    builder.from_id(db, old_params)
                    for db in design_builder_ids]
            self.simulation_builders = [
                    builder.from_id(db, old_params)
                    for db in simulation_builder_ids]
            self.parameters = old_params
            self.top_module = old_params['top_module']
        else:
            self.params_helper.write(parameters)
            self.design_builders = design_builders
            self.simulation_builders = simulation_builders
            self.parameters = parameters
            self.top_module = top_module
            files_and_ip = make_files_and_ip(
                directory=directory,
                design_builders=design_builders,
                simulation_builders=simulation_builders,
                parameters=parameters,
                top_module=top_module,
                exclude_fn=exclude_fn,
                )
            files_and_ip['design_files'] += additional_files
        super().__init__(
            directory=directory,
            files_and_ip=files_and_ip,
            overwrite_ok=overwrite_ok)

    def get_hash(self):
        return get_hash_from_builders(
            directory=self.directory,
            design_builders=self.design_builders,
            simulation_builders=self.simulation_builders,
            top_module=self.top_module,
            parameters=self.parameters,
            )

