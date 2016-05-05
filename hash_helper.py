import os
import logging

logger = logging.getLogger(__name__)


class HashHelper(object):

    def __init__(self, directory, get_hash):
        self.directory = directory
        self.get_hash = get_hash

    def hash_fn(self):
        hash_fn = os.path.join(self.directory, 'hash.txt')
        return hash_fn

    def read(self):
        hash_fn = self.hash_fn()
        if not os.path.exists(hash_fn):
            h = None
        else:
            with open(hash_fn, 'rb') as f:
                h = f.read()
        return h

    def write(self, h=None):
        '''
        Write a record of the project's hash.
        '''
        if h is None:
            h = self.get_hash()
        hash_fn = self.hash_fn()
        with open(hash_fn, 'wb') as f:
            f.write(h)

    def is_changed(self):
        old_hash = self.read()
        new_hash = self.get_hash()
        logger.debug('old hash {} new hash {}'.format(old_hash, new_hash))
        return (old_hash != new_hash) and (old_hash is not None)
