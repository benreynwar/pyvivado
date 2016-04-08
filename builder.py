import collections
import logging
import inspect

logger = logging.getLogger(__name__)

# `Builder` objects are registered here.
# They are registered as a package if they take top level parameters
# (i.e. the set of parameters that specify the whole design).
package_register = {}
# They are registered as modules if they take more local parameters.
module_register = {}

def make_hashable(d):
    if isinstance(d, collections.OrderedDict):
        hs = []
        for k, v in d.items():
            hs.append((k, make_hashable(v)))
        h = tuple(hs)
    elif isinstance(d, dict):
        hs = []
        for k, v in d.items():
            hs.append((k, make_hashable(v)))
        h = frozenset(hs)
    elif (isinstance(d, list) or isinstance(d, tuple)):
        hs = []
        for v in d:
            hs.append(make_hashable(v))
        h = tuple(hs)
    elif (isinstance(d, set) or isinstance(d, frozenset)):
        hs = []
        for v in d:
            hs.append(make_hashable(v))
        h = frozenset(hs)        
    elif not isinstance(d, collections.Hashable):
        logger.error('Cannot hash {}'.format(d))
        h = d
    else:
        h = d
    return h


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

    def __init__(self, params, package_name=None):
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

    def _id(self):
        '''
        Generates a unique ID for the module.  This is useful so that
        we can track which modules have been generated and we don't generate
        the same one twice.
        '''
        if self.package_name is not None:
            _id = self.package_name
        else:
            _id = (self.__class__, make_hashable(self.params))
        return _id

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


def get_all_builders(top_builders=[], top_package=None, top_params={}):
    '''
    Takes a list of builders and generate a list of all required builders
    by looking at their dependencies.
    '''
    done_builders = {}
    todo_builders = {}
    for top_builder in top_builders:
        todo_builders[top_builder._id()] = top_builder
    if top_package:
        package_builder = package_register[package_name](top_params)
        todo_builders[package_builder._id()] = package_builder
    while todo_builders:
        active_id = list(todo_builders.keys())[0]
        active_builder = todo_builders[active_id]
        del todo_builders[active_id]
        done_builders[active_id] = active_builder
        for new_builder in active_builder.required_builders():
            _id = new_builder._id()
            if _id not in done_builders:
                todo_builders[_id] = new_builder
        for new_package in active_builder.required_packages():
            if new_package not in done_builders:
                package_builder = package_register[new_package](top_params)
                assert(package_builder._id() == new_package)
                todo_builders[new_package] = package_builder
    builders = done_builders.values()
    return builders

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
    filenames = set()
    ips = []
    ip_hashs = set()
    for builder in builders:
        ips += builder.required_ips()
        filenames |= set(builder.required_filenames(directory))
    return {
        'filenames': filenames,
        'ips': condense_ips(ips),
    }

def build_all(directory, top_builders=[], top_package=None, top_params={},
              false_directory=None):
    '''
    Takes a few top level builders, works out what all the
    dependencies are, generates all the required files, and returns
    the filenames and IP information of the requirements.

    '''
    builders = get_all_builders(top_builders=top_builders,
                                top_package=top_package,
                                top_params=top_params)
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
    
