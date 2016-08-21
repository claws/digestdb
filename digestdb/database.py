
import logging
import os

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .model import Base, Category, Digest
from .hashify import data_digest, file_digest, digest_filepath

# type annotations
from typing import (
    Dict, Generator, List, Optional, Sequence, Tuple, Union)
import datetime
from sqlalchemy.engine import Engine
from sqlalchemy.orm.session import Session

# type aliases
PutItem = Tuple[str, bytes, Union[datetime.datetime, None]]
QueryResult = Sequence[Tuple[bytes, str, int, datetime.datetime]]


logger = logging.getLogger(__name__)


def write_database_file(digest: bytes,
                        data: bytes,
                        data_dir: str,
                        dir_depth: int) -> None:
    '''
    Writes a binary database item to the file system.

    This function first creates the filename and file path from the digest
    information. It creates the directory tree is necessary and then writes
    the data into the file.

    :param digest: a bytes object representing a hash of some data.

    :param data: a bytes object containing the binary data to be stored by the
      database.

    :param data_dir: the database's root directory path where binary data is
      being stored.

    :param dir_depth: the number of directories to being used to spread files.

    :raises: Exception if a duplicate filename is detected.
    '''
    fpath = os.path.join(
        data_dir, digest_filepath(digest, dir_depth=dir_depth))

    # Create directories as required
    os.makedirs(os.path.dirname(fpath), exist_ok=True)

    if os.path.exists(fpath):
        raise Exception(
            'Duplicate file detected: {}'.format(fpath))

    with open(fpath, 'wb') as fd:
        fd.write(data)


def read_database_file(digest: bytes,
                       data_dir: str,
                       dir_depth: int,
                       chunk_size: int = 2**20) -> Generator[bytes, None, None]:
    '''
    Return the binary data associated with the digest.

    This method is implemented as a generator that returns one chunk per
    iteration. This is to avoid reading large files completely into memory.

    .. code-block:: python

        for chunk in read_database_file():
            print(chunk)

    :param digest: a bytes object representing a hash of some data.

    :param data_dir: the database's root directory path where binary data is
      being stored.

    :param dir_depth: the number of directories to being used to spread files.

    :param chunk_size: the number of bytes to read from the file per
      iteration.

    :raises: OSError exception if the resolved file does not exist.
    '''
    fpath = os.path.join(data_dir, digest_filepath(
        digest, dir_depth=dir_depth))
    with open(fpath, 'rb') as fd:
        for chunk in iter(lambda: fd.read(chunk_size), b''):
            yield chunk


def sync_file_system(data_dir: str,
                     db: 'DigestDB') -> List[bytes]:
    '''
    Walk the file system under the ``data_dir`` to find items that are not
    listed in the database.

    :param data_dir: the database's root directory path where binary data is
      being stored.

    :param db: a database object.

    :return: a list of digests found on the file system that are not found
      in the database.
    '''
    items = []
    for dirpath, dirnames, filenames in os.walk(data_dir):
        for filename in filenames:
            # filename is the str dump of the hex digest
            digest = bytes.fromhex(filename)
            if not db.exists(digest):
                items.append(digest)
    return items


class DigestDB(object):
    '''
    This class implements the data access layer for the binary database.

    The database is comprised of two parts:

    - the metadata database that stores the hash of each binary blob.

    - a filesystem directory structure for storing the binary blobs in
      filenames that match the hash digest of the blob.

    The directories down which data blobs are stored are created only when
    required. The number of directories used to balance the data over a
    number of directories is related to the total number of data items that
    are expected to be stored in the database. By default the depth is 3.
    This is suitable for storing lots (billions) of data files.

    The data is stored in the database is categorised so that queries can
    be run later to retrieve blobs from a certain category. Categories
    must be added to the database before data items can be associated with
    the category.
    '''

    def __init__(self,
                 db_dir: str,
                 filename: str = 'digestdb.db',
                 data_dir: str = 'digestdb.data',
                 dir_depth: int = 3,
                 hash_name: str = 'sha256') -> None:
        '''

        :param db_dir: the top level directory that the blob database will use
          for its file and directory artefacts. The directory must exist.
          If the directory does not exist then an exception is raised.
          The path can include the `~` which will be translated into the user
          home directory.

        :param filename: an database explicit file to use. This parameter is
          only necessary when you want to resume writing to an existing
          database or perhaps in a replay scenario.

        :param dir_depth: defines the number of directories down which the
          binary files are stored. The directories are based on the first N
          characters of the hash digest. The default value is 3 which should
          be sufficient for large databases.

        :param hash_name: the name of a hash calculator. Defaults to sha256.
        '''
        if not os.path.exists(db_dir):
            raise Exception(
                'Invalid db_dir: {}'.format(db_dir))
        self.db_dir = os.path.abspath(os.path.expanduser(db_dir))
        self.filename = os.path.join(self.db_dir, filename)
        self.data_dir = os.path.join(self.db_dir, data_dir)
        self.dir_depth = dir_depth
        self.hash_name = hash_name
        self.db_url = 'sqlite:///{}'.format(self.filename)
        self.lock_file = '{}.lock'.format(
            os.path.splitext(self.filename)[0])

        self.engine = None  # type: Engine
        self.sessionmaker = None  # type: sessionmaker
        self.session = None  # type: Session

    def __repr__(self) -> str:
        return "<DigestDB '{}'>".format(self.db_dir)

    def open(self) -> None:
        ''' Open the database.

        This will create the database file if necessary or will open an
        existing file if one is present.
        '''
        if os.path.exists(self.lock_file):
            raise Exception(
                'Database is already open. Close database or '
                'remove .lock file: {}'.format(self.lock_file))

        # create lock file
        with open(self.lock_file, 'w'):
            pass

        self.engine = create_engine(self.db_url)
        Base.metadata.create_all(self.engine)  # creates the table metadata
        self.sessionmaker = sessionmaker(bind=self.engine)
        self.session = self.sessionmaker()

    def close(self) -> None:
        ''' Close the database '''
        if self.session:
            self.session.close()
            self.engine.dispose()
        os.remove(self.lock_file)
        self.session = None
        self.engine = None
        self.sessionmaker = None

    @contextmanager
    def session_scope(self):
        '''
        Provide a transactional scope around a series of operations.

        This context manager can make it easier to perform database actions.
        The developer can avoid adding the commit or rollback boilerplate
        code everywhere.

        .. code-block:: python

            with db.session_scope() as session:
                item = model.Item(id='blah')
                session.add(item)

        When with statement is exited the session is commited. If an error
        occurs the session is rolled back.
        '''
        try:
            session = self.sessionmaker()
            yield session
            session.commit()
        except:
            session.rollback()
            raise

    # ------------------------------------------------------------------------
    # Category methods
    #

    def put_category(self,
                     label: str,
                     description: str = '') -> None:
        ''' Add a category to digestdb.

        If the category already exists then an exception is raised.

        :param label: a short string that can be used to identify the category.
          The name will be used as the primary key and hence should be unique.

        :param description: a longer description of the category.

        :return: a category identifier. Each data item added to digestdb needs
          to be associated with a category. This allows efficient retrieval
          of certain kinds of blobs at a later time.
        '''
        try:
            self.get_category(label)
        except Exception:
            c = Category(label=label, description=description)
            self.session.add(c)
            self.session.commit()
        else:
            raise Exception('Category {} already exists'.format(label))

    def get_category(self,
                     label: str) -> Tuple[str, str]:
        '''
        Return the contents of a category.

        :param label: a short string that uniquely identifies a category.

        :return: a 2-tuple containing the category label and description.

        :raises: an exception is raised if the category is not found.
        '''
        try:
            c = self.session.query(Category).filter_by(label=label).one()
            return (c.label, c.description)
        except Exception:
            raise Exception(
                'Category {} not found in database'.format(label)) from None

    def query_category(self,
                       **filters: Dict[str, str]) -> List[Tuple[str, str]]:
        ''' Query the categories in the database.

        This query supports a limited number of filter keyword arguments.
        The supported query keywords are:

        :keyword label: a label to use as a query filter.

        :keyword description: a description sub-string that will be used as
          a query filter.

        :return: a list of matched categories as 2-tuple containing the
          category label and description

        '''
        query = self.session.query(Category)

        label = filters.get('label')
        if label:
            query = query.filter_by(label=label)

        description = filters.get('description')
        if description:
            query = query.filter(Category.description.contains(description))

        return [(c.label, c.description) for c in query]

    def count_category(self) -> int:
        ''' Return the number of category items in the database. '''
        return self.session.query(Category).count()

    # ------------------------------------------------------------------------
    # Data methods
    #

    def _put_data_digest(self,
                         category: str,
                         digest: bytes,
                         size: int,
                         timestamp: datetime.datetime = None):
        '''
        Add an item, with a pre-computed hash, to the database.

        This method is used to update the database for data items that are
        already present on the file system.

        :param category: a category label that must match an existing
          category in the database.

        :param digest: a bytes object representing the hash digest of the data
          item.

        :param size: an integer representing the size of the data blob.

        :param timestamp: a specific timestamp to store alongside the metadata
          instead of the default `now` timestamp used if this field if left
          as its default of None.

        :return: a bytes object representing the hash digest of the data item
        '''
        b = Digest(digest=digest, category_label=category,
                   byte_size=size, timestamp=timestamp)
        self.session.add(b)
        self.session.commit()
        return digest

    def put_data(self,
                 category: str,
                 data: bytes,
                 timestamp: datetime.datetime = None) -> bytes:
        '''
        Add a data item to the database.

        :param category: a category label that must match an existing
          category in the database.

        :param data: the binary data to be stored in the database.

        :param timestamp: a specific timestamp to store alongside the metadata
          instead of the default `now` timestamp used if this field if left
          as its default of None.

        :return: a bytes object representing the hash digest of the data item
        '''
        digest = data_digest(data, hash_name=self.hash_name)
        write_database_file(digest, data, self.data_dir, self.dir_depth)
        self._put_data_digest(
            category, digest, len(data), timestamp=timestamp)
        return digest

    def put_data_many(self,
                      *items: PutItem) -> List[bytes]:
        '''
        Add a list of data items to the database.

        :param items: a list of items to add to the database. Items are
          expected to be 3-tuples of (category_id, data, timestamp). If
          timestamp is None then the current time will be used as the
          timestamp field in the database.

        :return: a list of bytes object representing the hash digest of the
          data items
        '''
        digests = []
        for item in items:
            category, data, timestamp = item
            digests.append(self.put_data(category, data, timestamp))
        return digests

    def put_file(self,
                 category: str,
                 filepath: str,
                 timestamp: datetime.datetime = None) -> bytes:
        '''
        Add the contents of a file to digestdb.

        :param category: a category label that must match an existing
          category that was previously added to the database.

        :param timestamp: a specific timestamp to store alongside the metadata
          instead of the default `now` timestamp used if this field if left
          as its default of None.

        :return: a bytes object representing the hash digest of the data item
        '''
        digest = file_digest(filepath, hash_name=self.hash_name)
        with open(filepath, 'rb') as fd:
            data = fd.read()
        write_database_file(digest, data, self.data_dir, self.dir_depth)
        self._put_data_digest(
            category, digest, len(data), timestamp=timestamp)
        return digest

    def get_data(self, digest: bytes) -> bytes:
        ''' Return the contents of a data item.

        :param digest: a bytes object representing the hash digest of the
          data item.

        :return: bytes
        '''
        # Go straight to the filesystem to fetch a data item.
        # Depending on the size of the objects it may be useful to
        # fetch the metadata from the database first as the size could
        # be used to choose an optimal chunk_size value.
        try:
            return b''.join(
                chunk for chunk in read_database_file(
                    digest, self.data_dir, self.dir_depth))
        except OSError:
            logger.exception('Could not get file matching: {}'.format(digest))
            return None

    def query_data(self,
                   **filters: Dict[str, str]) -> QueryResult:
        ''' Query data items in the database.

        This query supports a limited number of filter keyword arguments.
        The supported query keywords are:

        :keyword category: a label to use as a category query filter.

        :return: a list of matched blobs as 4-tuple containing the
          digest, category_label, byte_size, timestamp.

        '''
        query = self.session.query(Digest)

        category = filters.get('category')
        if category:
            query = query.filter_by(category_label=category)

        return [
            (b.digest, b.category_label, b.byte_size, b.timestamp) for b in query]

    def delete_data(self,
                    digest: bytes) -> None:
        ''' Delete a data item from the database '''
        try:
            b = self.session.query(Digest).filter_by(digest=digest).one()
            self.session.delete(b)
            self.session.commit()
        except Exception:
            pass

        try:
            os.remove(
                os.path.join(self.data_dir, digest_filepath(
                    digest, dir_depth=self.dir_depth)))
        except OSError:
            pass

    def exists(self, digest: bytes) -> bool:
        ''' Check if an entry exists in the database for the digest.

        This will check both the database and the file system.

        :param digest: a bytes object representing the hash digest of the
          data item.

        :return: a boolean indicating if the item is present in the database.
        '''
        present_in_db = False
        present_in_fs = False

        try:
            self.session.query(Digest).filter_by(digest=digest).one()
            present_in_db = True
        except Exception:
            pass

        present_in_fs = os.path.exists(
            os.path.join(self.data_dir, digest_filepath(
                digest, dir_depth=self.dir_depth)))

        result = present_in_db and present_in_fs

        if not result:
            logger.debug(
                '%x not found in database. db=%s, fs=%s',
                digest, present_in_db, present_in_fs)

        return result

    def count_data(self) -> int:
        ''' Return the number of data items in the database. '''
        return self.session.query(Digest).count()
