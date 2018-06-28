import os
import logging
import hashlib
import shutil
import time

from pyvivado import utils
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
    hashable_ips = []
    for ip in ips:
        params = ip[1]
        hashable_params = sorted(list(params.items()))
        hashable_ips.append((ip[0], hashable_params, ip[2]))
    # Check that names are unique
    names = [a[2] for a in ips]
    assert(len(names) == len(set(names)))
    design_files_hash = utils.files_hash(design_files)
    logger.debug(str(simulation_files))
    simulation_files_hash = utils.files_hash(simulation_files)
    # FIXME: Not sure whether this will work properly for
    # the ips
    ips_hash = str(tuple(hashable_ips)).encode('ascii')
    design_files_hash = utils.files_hash(design_files)
    simulation_files_hash = utils.files_hash(simulation_files)
    logger.debug('Making hash from files_and_ip: design_files={}, simulation_files={}, ips={}'.format(design_files_hash, simulation_files_hash, ips_hash))
    h.update(design_files_hash)
    h.update(simulation_files_hash)
    h.update(ips_hash)
    return h.digest()


def try_make_hash_directory(directory):
    try:
        os.mkdir(directory)
        success = True
    except FileExistsError:
        success = False
    return success


def make_hash_directory(directory):
    if not try_make_hash_directory(directory):
        logger.warning('Temp directory for hash already exists. Waiting to see if it is deleted.')
        max_waits = 10
        n_waits = 0
        while ((not try_make_hash_directory(directory)) and
               (n_waits < max_waits)):
            time.sleep(1)
            n_waits += 1
        if n_waits >= max_waits:
            raise Exception('temp directory for hash already exists. {}'.format(directory))


class BaseProjectException(Exception):
    pass


class OverwriteForbiddenException(BaseProjectException):
    pass


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
                        raise OverwriteForbiddenException()
                    else:
                        self.file_helper.write(self.files_and_ip, overwrite_ok=True)
            else:
                self.file_helper.write(files_and_ip)
        else:
            max_waits =5 
            n_waits = 0
            files_and_ip = self.file_helper.read()
            # Sometimes the project has just been created and there hasn't been
            # time for this info to be written.
            # This waits to see if that is the case.
            if files_and_ip is None:
                logger.warning('Files and IP not available.  Waiting in the hope that they will be written soon.')
            while (files_and_ip is None) and (n_waits < max_waits):
                time.sleep(1)
                n_waits += 1
                files_and_ip = self.file_helper.read()
        self.files_and_ip = files_and_ip
        #if self.hash_helper.is_changed():
        #    if not overwrite_ok:
        #        raise OverwriteForbiddenException()
        if self.files_and_ip is None:
            raise BaseProjectException('No Files and IP specified')
        self.hash_helper.write()

    def get_hash(self):
        h = get_hash(self.files_and_ip)
        logger.debug('got hash and it is {}'.format(h))
        return h 

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

