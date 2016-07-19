import logging
import inspect
import os
import subprocess
import json

from pyvivado.params_helper import make_constant_hashable, make_hashable


logger = logging.getLogger(__name__)

# `Builder` objects are registered here.
# They are registered as a package if they take top level parameters
# (i.e. the set of parameters that specify the whole design).
package_register = {}
# They are registered as modules if they take more local parameters.
module_register = {}


def from_id(_id, top_params):
    as_tuple = json.loads(_id)
    if as_tuple[0] == 'package':
        b = package_register[as_tuple[1]](top_params)
    elif as_tuple[0] == 'not_package':
        b = module_register[as_tuple[1]](as_tuple[2], top_params)
    else:
        raise ValueError(
            '_id is not in form expected for a Builder "{}".'.format(_id))
    return b


class Builder(object):
    '''
    Responsible for generating and specifying the files and IPs
    required for a module.

    Each module creates a subclass of this.
    '''

    # Hacky solution so that we can have broken modules without
    # worrying about whether they're getting included in any other
    # modules.
    # Override to True in builders of broken modules.
    broken = False

    def __init__(self, params, package_name=None, name=None):
        '''
        `params`: The parameters necessary to generate the module files.
        `package_name`: Send in the name of the package if this builder
             is specifying a package rather than a module.
        '''
        if self.broken:
            raise Exception('This module is broken.  Do not use.')
        self.params = params
        self.constants = {}
        # Simple filenames is a helper for simple builders where the
        # file already exist and don't need to be generated.
        self.simple_filenames = []
        # A list of (ip name, ip parameters, module name) for the IP
        # blocks that will be used by this module.
        self.ips = []
        # A list of builders necessary to generate the modules that
        # will be used in this module.
        self.builders = []
        # A list of packages required by this module.
        self.packages = []
        # The name of this package (is this is a package rather than a module)
        self.package_name = package_name
        self.name = name
        if self.name is None:
            builder_name = self.__class__.__name__[:-len('Builder')]
            self.name = builder_name

    def _id(self):
        '''
        Generates a unique ID for the module.  This is useful so that
        we can track which modules have been generated and we don't generate
        the same one twice.
        We should also be able to regenerated from the id.
        ie. It can be saved to a file to regenerated object later.
        '''
        if self.package_name is not None:
            as_tuple = ('package', self.package_name)
        else:
            as_tuple = ('not_package', self.name,
                        make_constant_hashable(self.params))
        _id = json.dumps(as_tuple)
        return _id

    def group_id(self):
        return None

    def make_group_builder(self):
        return None

    def set_group_builder(self):
        raise Exception('Unimplemented')

    def required_filenames(self, directory):
        '''
        Returns the files required to build this module.  It does not include
        files required by other builders that build the dependencies for
        this module.

        Override this method for more complex builders.
        '''
        return self.simple_filenames

    def required_ips(self):
        '''
        Returns a list of (ip name, ip parameters, module name) for the IP
        blocks that will be used by this module.

        Override this method for more complex builders.
        '''
        return self.ips

    def required_builders(self):
        '''
        Returns a list of builders that make the dependencies of this
        module.

        Override this method for more complex builders.
        '''
        return self.builders

    def required_packages(self):
        '''
        Returns a list of all the packages that this module requires.

        Override this method for more complex builders.
        '''
        return self.packages

    def build(self, directory, false_directory=None, top_params={}):
        '''
        Complex builders override this method to generate the required
        files.
        '''
        pass


def run_sbt_command(sbtdir, command):
    cwd = os.getcwd()
    os.chdir(sbtdir)
    command = ['sbt', command]
    subprocess.call(command)
    os.chdir(cwd)


def params_from_xco(xco_filename):
    '''
    Takes a Xilinx XCO file and parses it to get the IP parameters.
    '''
    params = {}
    with open(xco_filename, 'r') as f:
        for line in f:
            if line.startswith('CSET'):
                remainder = line[5:]
                param_name, value = remainder.split('=')
                params[param_name] = value
    return params


def get_all_builders(top_builders=[], top_package=None, top_params={}, exclude_fn=None):
    '''
    Takes a list of builders and generate a list of all required builders
    by looking at their dependencies.
    '''
    group_builders = {}
    done_builders = {}
    next_level_builders = {}
    for top_builder in top_builders:
        next_level_builders[top_builder._id()] = top_builder
    if top_package:
        package_builder = package_register[top_package](top_params)
        next_level_builders[package_builder._id()] = package_builder
    builder_level = 0
    done_levels = {}
    all_builders = {}
    while next_level_builders:
        this_level_builders = next_level_builders
        next_level_builders = {} 
        for active_id in this_level_builders:
            # This allows us to exclude some builders.
            # Useful if we have already synthesised some subset of the design
            # and wish to handle that independently.
            if exclude_fn and exclude_fn(active_id):
                continue
            active_builder = this_level_builders[active_id]
            group_id = active_builder.group_id()
            if group_id is not None:
                if group_id not in group_builders:
                    group_builder = active_builder.make_group_builder()
                    group_builders[group_id] = group_builder
                    all_builders[group_id] = group_builder
                else:
                    group_builder = group_builders[group_id]
                done_levels[group_id] = builder_level
                group_builders[group_id].add(active_builder)
                required_builders = group_builder.required_builders()
                required_packages = group_builder.required_packages()
            else:
                all_builders[active_id] = active_builder
                done_levels[active_id] = builder_level
                required_builders = active_builder.required_builders()
                required_packages = active_builder.required_packages()
            for new_builder in required_builders:
                _id = new_builder._id()
                next_level_builders[_id] = new_builder
            for new_package in required_packages:
                package_builder = package_register[new_package](top_params)
                package_id = package_builder._id() 
                next_level_builders[package_id] = package_builder
        builder_level += 1
        if builder_level > 100:
            import pdb
            pdb.set_trace()
    grouped_by_level = [[] for i in range(builder_level)]
    for active_id in done_levels:
        builder_level = done_levels[active_id]
        grouped_by_level[builder_level].append(all_builders[active_id])
    ordered_builders = []
    for group in reversed(grouped_by_level):
        group_dict = dict([(g._id(), g) for g in group])
        keys = list(group_dict.keys())
        keys.sort()
        ordered_builders += [group_dict[k] for k in keys]
    return ordered_builders


def condense_ips(ips):
    '''
    Remove duplicates from a list of IPs.
    '''
    condensed_ips = []
    ip_hashs = set()
    for ip in ips:
        ip_hash = make_hashable(ip)
        if ip_hash not in ip_hashs:
            condensed_ips.append(ip)
            ip_hashs.add(ip_hash)
    return condensed_ips


def get_requirements(builders, directory):
    '''
    Get all the files and IPs required by a list of builders.
    '''
    filenames = []
    ips = []
    ip_hashs = set()
    for builder in builders:
        ips += builder.required_ips()
        for fn in builder.required_filenames(directory):
            if fn not in filenames:
                filenames.append(fn)
    return {
        'filenames': filenames,
        'ips': condense_ips(ips),
    }


def build_all(directory, top_builders=[], top_package=None, top_params={},
              false_directory=None, exclude_fn=None):
    '''
    Takes a few top level builders, works out what all the
    dependencies are, generates all the required files, and returns
    the filenames and IP information of the requirements.

    '''
    builders = get_all_builders(top_builders=top_builders,
                                top_package=top_package,
                                top_params=top_params,
                                exclude_fn=exclude_fn,)
    for builder in builders:
        argspec = inspect.getargspec(builder.build)
        # Don't force all builders to take 'false_directory' or
        # 'top_params' when almost none need it.
        kwargs = {'directory': directory}
        if 'false_directory' in argspec.args:
            kwargs['false_directory'] = false_directory
        if 'top_params' in argspec.args:
            kwargs['top_params'] = top_params
        builder.build(**kwargs)
    requirements = get_requirements(builders, directory)
    return requirements


def make_simple_builder(filenames=[], builders=[], ips=[]):
    '''
    Construct a builder that takes no parameters.
    '''
    class SimpleBuilder(Builder):

        def __init__(self, params, package_name=None):
            assert(params == {})
            super().__init__(params=params, package_name=package_name)
            self.simple_filenames = filenames
            self.builders = builders
            self.simple_ips = ips

    return SimpleBuilder


def make_template_builder(template_fn):
    '''
    Construct a Builder that formats a template.
    '''
    possible_endings = ('.vhd.t', '.v.t', '.sv.t')
    stem = None
    for ending in possible_endings:
        if template_fn[-len(ending):] == ending:
            stem = template_fn[:len(ending)]
            suffix = template_fn[-len(ending):]
    if stem is None:
        raise ValueError('Template {} does not end with an expected ending {}').format(
            template_fn, possible_endings)

    class TemplateBuilder(Builder):

        def __init__(self, params):
            super().__init__(params)
            self.params_hash = hash(make_hashable(params))

        def filename(self, directory):
            return os.path.join(
                directory, '{}{}{}'.format(stem, self.params_hash, suffix))
