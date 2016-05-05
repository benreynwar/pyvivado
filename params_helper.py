import os
import json


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

    def write(self, params):
        '''
        Write the parameters that were used to generate this project.
        '''
        if os.path.exists(self.fn):
            raise Exception('Parameters file already exists.')
        as_json = self.text(params)
        with open(self.fn, 'w') as f:
            f.write(as_json)


class FilesHelper():

    def __init__(self, directory):
        self.fn = os.path.join(directory, 'files_and_ip.txt')
        self.params_helper = ParamsHelper(self.fn)

    def read(self):
        faips = self.params_helper.read()
        if faips is not None:
            for k in ('design_files', 'simulation_files', 'ips'):
                faips[k] = set(faips[k])
        return faips

    def write(self, faips):
        for k in ('design_files', 'simulation_files', 'ips'):
            faips[k] = list(faips[k])
        self.params_helper.write(faips)
