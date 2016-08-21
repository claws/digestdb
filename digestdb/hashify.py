
import hashlib
import os


def data_digest(data: bytes, hash_name: str = 'sha256') -> bytes:
    '''
    Return a hash representing the binary data.

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


def file_digest(filename: str,
                hash_name: str = 'sha256',
                chunk_size: int = 2**20) -> bytes:
    '''
    Return a hash representing the contents of a file.

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


def digest_filepath(digest: bytes,
                    dir_depth: int = 3) -> str:
    '''
    Convert a digest into its equivalent database filepath.

    The filepath will look like the example below when ``dir_depth=3``:

    .. code-block:: console

        8f/dd/8b/8fdd8b7dfa0d7d4f761da78e76d62ec4bee3b1847a6ad48507090e13752b2d

    :param digest: a bytes object representing a hash of some data.

    :return: a storage filepath for the file associated with the digest.
    '''
    if not isinstance(dir_depth, int) or dir_depth < 1:
        raise Exception(
            'Invalid dir_depth. Value must be an integer, 1 or greater, '
            'got: %s, %s'.format(type(dir_depth), dir_depth))

    # typeshed #488, hex missing from bytes definition
    filename = digest.hex()  # type: ignore

    # Extract two characters from the filename for each dir_depth
    # to construct the direcory elements.
    parts = []  # type: List[str]
    for i in range(0, dir_depth * 2, 2):
        dir_element = filename[i:i + 2]
        parts.append(dir_element)
    parts.append(filename)
    filepath = os.path.join(parts[0], *parts[1:])
    return filepath
