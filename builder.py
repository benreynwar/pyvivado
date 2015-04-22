import collections
import logging

logger = logging.getLogger(__name__)

package_register = {}
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

    def __init__(self, params, package_name=None):
        self.params = params
        self.simple_filenames = []
        self.ips = []
        self.builders = []
        self.packages = []
        self.package_name = package_name

    def _id(self):
        if self.package_name is not None:
            _id = self.package_name
        else:
            logger.debug(self)
            _id = (self.__class__, make_hashable(self.params))
        return _id

    def required_filenames(self, directory):
        return self.simple_filenames

    def required_ips(self):
        return self.ips

    def required_builders(self):
        return self.builders

    def required_packages(self):
        return self.packages

    def build(self, directory):
        pass


def params_from_xco(xco_filename):
    params = {}
    with open(xco_filename, 'r') as f:
        for line in f:
            if line.startswith('CSET'):
                remainder = line[5:]
                param_name, value = remainder.split('=')
                params[param_name] = value
    return params


def get_all_builders(top_builders=[], top_package=None, top_params={}):
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
                logger.debug(new_package)
                package_builder = package_register[new_package](top_params)
                assert(package_builder._id() == new_package)
                todo_builders[new_package] = package_builder
    builders = done_builders.values()
    return builders

def condense_ips(ips):
    condensed_ips = []
    ip_hashs = set()
    for ip in ips:
        ip_hash = make_hashable(ip)
        if ip_hash not in ip_hashs:
            condensed_ips.append(ip)
            ip_hashs.add(ip_hash)
    return condensed_ips

def get_requirements(builders, directory):
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

def build_all(directory, top_builders=[], top_package=None, top_params={}):
    builders = get_all_builders(top_builders=top_builders,
                                top_package=top_package,
                                top_params=top_params)
    for builder in builders:
        builder.build(directory)
    requirements = get_requirements(builders, directory)
    return requirements
