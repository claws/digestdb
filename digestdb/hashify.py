
import hashlib
import os


def data_digest(data, hash_name='sha256'):
    ''' Return a hash representing the binary data.

    :param data: a bytes object representing the object to be hashed.

    :param hash_name: the name of a hash calculator. Defaults to sha256.

    :return: a bytes object representing the digest of the data.
    '''
    if not isinstance(data, bytes):
        raise Exception(
            'Invalid data type. Expected bytes but got {}'.format(
                type(data)))

    h = hashlib.new(hash_name)
    h.update(data)
    return h.digest()


def file_digest(filename, hash_name='sha256', chunk_size=2**20):
    ''' Return a hash representing the contents of a file.

    :param data: a bytes object representing the object to be hashed.

    :param hash_name: the name of a hash calculator. Defaults to sha256.

    :param chunk_size: the size of data to read at a time from the file.
      This avoids needing to read an entire file into memory to calculate
      its hash which is useful for very large files.

    :return: a bytes object representing the digest of the data.
    '''
    h = hashlib.new(hash_name)
    with open(filename, 'rb') as fd:
        for chunk in iter(lambda: fd.read(chunk_size), b''):
            h.update(chunk)
    return h.digest()


def digest_filepath(digest, dir_depth=3):
    ''' Convert a digest into its equivalent database filepath.

    The filepath will look like the example below when `dir_depth=3`:

    .. code-block:: console

        8f/dd/8b/8fdd8b7dfa0d7d4f761da78e76d62ec4bee3b1847a6ad48507090e13752b2d

    :param digest: a bytes object representing a hash of some data.

    :return: a storage filepath for the file associated with the digest.
    '''
    if not isinstance(dir_depth, int) or dir_depth < 1:
        raise Exception(
            'Invalid dir_depth. Value must be an int and greater'
            'than 1, got: %s, %s'.format(type(dir_depth), dir_depth))

    filename = digest.hex()
    # Extract two characters from the filename for each dir_depth
    dirnames = [filename[i:i + 2] for i in range(0, dir_depth * 2, 2)]
    return os.path.join(*dirnames, filename)
