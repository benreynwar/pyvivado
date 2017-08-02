import hashlib


def files_hash(fns):
    '''
    Generate a hash from the contents of several files.
    '''
    h = hashlib.sha1()
    for fn in fns:
        with open(fn, 'rb') as f:
            finished = False
            while not finished:
                buf = f.read(4096)
                if buf:
                    h.update(hashlib.sha1(buf).digest())
                else:
                    finished = True
    return h.digest()
