
import datetime
import logging
import itertools
import os
import tempfile

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .model import Base, Category, Blob
from .hashify import data_digest, digest_filepath


logger = logging.getLogger(__name__)


def write_database_file(digest, data, data_dir, dir_depth):
    ''' Write a binary database item to the file system.

    This method first creates the filename and file path from the digest
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

    # Managing lots of directories can be a pain. For example, at a default
    # depth of 3 directories that would be 16 million directories to create.
    # Deleting this many directories (e.g. during test runs) takes a very
    # long time. So, a directory is only created if a data file being stored
    # demands its presence.
    os.makedirs(os.path.dirname(fpath), exist_ok=True)

    if os.path.exists(fpath):
        raise Exception(
            'Duplicate file detected: {}'.format(fpath))

    with open(fpath, 'wb') as fd:
        fd.write(data)


def read_database_file(digest, data_dir, dir_depth, chunk_size=2**20):
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
    '''
    fpath = os.path.join(data_dir, digest_filepath(
        digest, dir_depth=dir_depth))
    assert os.path.exists(fpath)
    with open(fpath, 'rb') as fd:
        for chunk in iter(lambda: fd.read(chunk_size), b''):
            yield chunk


class BlobDB(object):
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

    def __init__(self, db_dir,
                 filename='blobdb.db',
                 data_dir='blobdb.data',
                 dir_depth=3):
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
        '''
        if not os.path.exists(db_dir):
            raise Exception(
                'Invalid db_dir: {}'.format(db_dir))
        self.db_dir = os.path.abspath(os.path.expanduser(db_dir))
        self.filename = os.path.join(self.db_dir, filename)
        self.data_dir = os.path.join(self.db_dir, data_dir)
        self.dir_depth = dir_depth
        self.db_url = 'sqlite:///{}'.format(self.filename)
        self.lock_file = '{}.lock'.format(
            os.path.splitext(self.filename)[0])

        self.engine = None
        self.sessionmaker = None
        self.session = None

    def open(self):
        ''' Open the database.

        This will create the database file if necessary and will open an
        existing file if on is present.
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

    def close(self):
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
        ''' Provide a transactional scope around a series of operations.

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

    def put_category(self, label, description=''):
        ''' Add a category to blobdb.

        If the category already exists then an exception is raised.

        :param label: a short string that can be used to identify the category.
          The name will be used as the primary key and hence should be unique.

        :param description: a longer description of the category.

        :return: a category identifier. Each data item added to blobdb needs
          to be associated with a category. This allows efficient retrieval
          of certain kinds of blobs at a later time.
        '''
        try:
            self.get_category(label)
        except Exception:
            c = Category(label=label, description=description)
            self.session.add(c)
            self.session.commit()  # commit to create a category_id
        else:
            raise Exception('Category {} already exists'.format(label))

    def get_category(self, label):
        ''' Return the contents of a category.

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

    def query_category(self, **filters):
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

    def count_category(self):
        ''' Return the number of category items in the database. '''
        return self.session.query(Category).count()

    # ------------------------------------------------------------------------
    # Data methods
    #

    def put_data(self, category, data, timestamp=None):
        ''' Add a data item to blobdb.

        :param category: a category label that must match an existing
          category that was previously added to the database.

        :param data: the binary data to be stored in the database.

        :param timestamp: a specific timestamp to store alongside the metadata
          instead of the default `now` timestamp used if this field if left
          as its default of None.

        :return: a bytes object representing the hash digest of the data item
        '''
        digest = data_digest(data)

        # write data to disk
        write_database_file(digest, data, self.data_dir, self.dir_depth)

        # add entry to database
        b = Blob(digest=digest, category_label=category,
                 byte_size=len(data), timestamp=timestamp)
        self.session.add(b)
        self.session.commit()

        return digest

    def put_data_many(self, *items):
        ''' Add many data items to blobdb.

        :param items: a list of tuples (category_id, data, [timestamp]).

        :return: a list of bytes object representing the hash digest of the
          data items
        '''
        digests = []
        for item in items:
            try:
                category, data = item
                timestamp = None
            except ValueError:
                category, data, timestamp = item

            digests.append(
                self.put_data(category, data, timestamp=timestamp))

        return digests

    # def put_file(self, category, filepath, timestamp=None):
    #     ''' Add the contents of a file to blobdb.

    #     This is just a convenience wrapper around `put` which efficiently
    #     reads the contents of the file and feeds it into put.

    #     :param category: a category label that must match an existing
    #       category that was previously added to the database.

    #     :param timestamp: a specific timestamp to store alongside the metadata
    #       instead of the default `now` timestamp used if this field if left
    #       as its default of None.
    #     '''
    #     # TODO: The digest calculator is implemented efficiently using a
    #     # generator to read the file in chunks while calculating the digest.
    #     # Ideally I would like a similar method to write the file into the
    #     # database file system. Naively this would involve two file reader
    #     # generators, so ideally I would like a chunked reader that would
    #     # be used once to compute the digest and write the file into the
    #     # database filesystem.

    #     digest = file_digest(filepath)

    #     with open(filepath, 'rb') as fd:
    #         data = fd.read()

    #     return self.put_data(category, data)

    def exists(self, digest):
        ''' Check if an entry exists in the database for the digest.

        This will check both the database and the file system.

        :param digest: a bytes object representing the hash digest of the
          data item.

        :return: a boolean indicating if the item is present in the database.
        '''
        present_in_db = False
        present_in_fs = False

        try:
            self.session.query(Blob).filter_by(digest=digest).one()
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

    def get_data(self, digest):
        ''' Return the contents of a blob.

        :param digest: a bytes object representing the hash digest of the
          data item.

        :return: a generator that returns chunks of the blob.
        '''
        # We can just go straight to the filesystem to fetch a blob.
        # Depending on the size of the objects it may be useful to
        # fetch the metadata from the database. The size could be
        # used to choose an optimal chunk_size value.
        try:
            return b''.join(
                c for c in read_database_file(
                    digest, self.data_dir, self.dir_depth))
            # parts = []
            # for c in read_database_file(digest, self.data_dir, self.dir_depth):
            #     parts.append(c)
            # return b''.join(parts)
        except OSError:
            logger.exception('Could not get file')
            return None

    def query_data(self, **filters):
        ''' Query data items in the database.

        This query supports a limited number of filter keyword arguments.
        The supported query keywords are:

        :keyword category: a label to use as a category query filter.

        :return: a list of matched blobs as 4-tuple containing the
          digest, category_label, byte_size, timestamp.

        '''
        query = self.session.query(Blob)

        category = filters.get('category')
        if category:
            query = query.filter_by(category_label=category)

        return [
            (b.digest, b.category_label, b.byte_size, b.timestamp) for b in query]

    def delete_data(self, digest):
        ''' Delete a data item from the database '''
        try:
            b = self.session.query(Blob).filter_by(digest=digest).one()
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

    def count_data(self):
        ''' Return the number of data items in the database. '''
        return self.session.query(Blob).count()
