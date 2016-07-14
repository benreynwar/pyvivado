import os
import json
import collections
from hashlib import sha1

from pyvivado import interface


def make_constant_hashable(d):
    if isinstance(d, dict):
        keys = list(d.keys())
        keys.sort()
        h = collections.OrderedDict([(k, d[k]) for k in keys])
        for k in keys:
            h[k] = make_constant_hashable(h[k])
    elif (isinstance(d, set) or isinstance(d, frozenset)):
        h = list(d)
        h.sort()
        for i in range(len(h)):
            h[i] = make_constant_hashable(h[i])
    elif isinstance(d, interface.Interface):
        h = d._id()
    else:
        h = d
    return h


def make_constant_hash(d):
    hashable = make_constant_hashable(d)
    params_hash = sha1(str(hashable).encode('ascii')).hexdigest()[:7]
    return params_hash


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
    elif isinstance(d, interface.Interface):
        h = d._id()
    elif not isinstance(d, collections.Hashable):
        logger.error('Cannot hash {}'.format(d))
        h = d
    else:
        h = d
    return h


class ParamsHelper(object):

    def __init__(self, fn):
        self.fn = fn

    def read(self):
        '''
        Read the parameters that were used to generate this project.
        '''
        if not os.path.exists(self.fn):
            params = None
        else:
            with open(self.fn, 'r') as f:
                params = json.load(f)
        return params

    @classmethod
    def text(cls, params):
        as_json = json.dumps(params, sort_keys=True,
                             indent=2, separators=(',', ': '))
        return as_json

    def write(self, params, overwrite_ok=False):
        '''
        Write the parameters that were used to generate this project.
        '''
        if os.path.exists(self.fn) and not overwrite_ok:
            raise Exception('Parameters file already exists.')
        as_json = self.text(params)
        with open(self.fn, 'w') as f:
            f.write(as_json)

    def has_changed(self, old_params):
        new_params = self.read()  
        old = make_hashable(old_params)
        new = make_hashable(new_params)
        return old != new


class FilesHelper():

    def __init__(self, directory):
        self.fn = os.path.join(directory, 'files_and_ip.txt')
        self.params_helper = ParamsHelper(self.fn)

    def read(self):
        faips = self.params_helper.read()
        if faips is not None:
            for k in ('design_files', 'simulation_files', 'ips'):
                faips[k] = list(faips[k])
        return faips

    def write(self, faips, overwrite_ok=False):
        for k in ('design_files', 'simulation_files', 'ips'):
            faips[k] = list(faips[k])
        self.params_helper.write(faips, overwrite_ok=overwrite_ok)

    def has_changed(self, faips):
        for k in ('design_files', 'simulation_files', 'ips'):
            faips[k] = list(faips[k])
        return self.params_helper.has_changed(faips)
