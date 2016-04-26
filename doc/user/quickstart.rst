Quickstart
==========


Database
--------

To start using the Blobdb you need to create a database. Let's create a
:class:`DigestDB` and tell it to use the current directory.

.. code-block:: python

    from digestdb import DigestDB

    db = DigestDB('.')

By default the :class:`DigestDB` will create a file called `digestdb.db`
and a directory called `digestdb.data`. The `digestdb.db` is a simple SQLite
database that stores the categories and digests of the blobs. The
`digestdb.data` is the top level directory in which all the binary blobs are
stored.

The :class:`DigestDB` does not do a whole lot when it is instantiated.
One of the few things it does do is check for a lock file. The
:class:`DigestDB` uses a lock file to ensure that it has exclusive
access to the data otherwise there is a risk of losing synchronisation between
the files on disk and those listing in the database.

If the :class:`DigestDB` encounters a lock file when starting up it will
report the error and shut down. The user is left to make the decision of what
to do next.

To actually get the :class:`DigestDB` to create the underlying database
so that binary data can be stored you must open the database.

.. code-block:: python

    db.open()



Conversely, when you are finished with the database it must be closed.

.. code-block:: python

    db.close()

If you re-open the database it will simply continue on from where it left off.

If you want to create a new database you can explicitly specify `filename` and
`data_dir`.

The :class:`DigestDB` takes a number of optional arguments. The
`dir_depth` is one of the most important settings and is disucssed in detail
in the following seciton.


Database Depth
++++++++++++++

To understand the database directory depth we need some background first.

There isn't any real limit on the number of files that can be stored in a
directory. However, anyone who has worked on projects that store lots of files
in a single directory can attest to it becoming very slow as the number of
files increases. The time it takes to list and checking for the existance of a
file increases as the number of files increase. So we need a strategy to
balance the files over some number of direcotries to avoid this problem.

The file path that determines where a blob is store will be created from the
blob's hash. As a new item is added to the database a SHA-256 hash is
calculated. This implementation uses a directory depth of 3 and hence it then
take the first three bytes from the hash digest and uses these to construct a
directory structure.

So for the following hash:

.. code-block:: console

        8fdd8b7dfa0d7d4f761da78e76d62ec4bee3b1847a6ad48507090e13752b2d

The directory structure used to store the data on the file system with a
directory depth of 1 would be:

.. code-block:: console

        8f/8fdd8b7dfa0d7d4f761da78e76d62ec4bee3b1847a6ad48507090e13752b2d

The directory structure used to store the data on the file system with a
directory depth of 3 would be:

.. code-block:: console

        8f/dd/8b/8fdd8b7dfa0d7d4f761da78e76d62ec4bee3b1847a6ad48507090e13752b2d

Each directory level adds 256 direcotries (\x00, \x01, ... \xfe, \xff). So
with a directory depth of we get 256 directories. With a depth of 2 we get
256 * 256 = 65536 and with a depth of 3 we get 256 * 256 * 256 = 16,777,216
directories.

The chosen directory depth can significantly impact cleanup operations.
Let's assume a naive implementation that creates all directories up front.
Without storing any data files at all, let's see how long it takes to
delete all of the directories. When `depth=1` it takes about 0.03 seconds.
When `depth=2` it takes about 10 seconds to remove the 65 thousand
directories. When `depth=3` it takes a very long time (2441 secs) to remove
the 16 million directories.

For this reason the directories down which data blobs are stored are created
only when required. This significantly reduces the time it takes to remove
transient databases - such as those used in unit tests.


The number of directories used to balance the data is related to the total
number of data items that are expected to be stored in the database. By
default the depth is 3. This is suitable for storing lots (billions) of data
files.

As an example, let's say we plan on having around 10 million files in the
database. The following table shows the expected files in each directory for
different directory depth settings.

+-------+-------------+---------------+
| depth | directories | files per dir |
+=======+=============+===============+
| 0     |           1 |  10,000,000.0 |
+-------+-------------+---------------+
| 1     |         256 |      39,062.5 |
+-------+-------------+---------------+
| 2     |      65,536 |         152.5 |
+-------+-------------+---------------+
| 3     |  16,777,216 |           0.6 |
+-------+-------------+---------------+

In this example a depth of 2 would be appropriate.

The maximum entries in a database for a column with a primary key of a
signed integer is 2,147,483,647. So let's bump the expected file items to 2
billion.

+-------+-------------+-----------------+
| depth | directories | files per dir   |
+=======+=============+=================+
|   0   |          1  | 2,000,000,000.0 |
+-------+-------------+-----------------+
|   1   |        256  |     7,812,500.0 |
+-------+-------------+-----------------+
|   2   |     65,536  |        30,517.6 |
+-------+-------------+-----------------+
|   3   | 16,777,216  |           119.2 |
+-------+-------------+-----------------+

In this example a depth of 3 seems more appropriate.


Categories
----------

Categories are used to group associated kinds of data in the database. They
provide a mechansim for efficient querying of data by category.

The selection of what constitutes a category depends on the scenario. Below
are some examples of how categories might be used to group different kinds of
data:

- when storing inter-process messages (e.g. for later analysis or replay)
  the categories might be the message kinds or identifiers.

- when storing web requests the categories might be route paths.

- when storing web server resources the categories might represent
  images, css, javascript, etc.

Categories must be added to the database before data items can be associated
with the category.

.. code-block:: python

    db.put_category(
        label='js', description='JavaScript resources')


Blobs
-----

This is why the DigestDB exists at all. DigestDB provides the developer with
capabilities to put, get delete and query blobs.

To add a blob to the database use `put_data`:

.. code-block:: python

    digest = db.put_data(category='js', data=b'\x00\x01...')

To check if data exists in the database use `exists`:

.. code-block:: python

    data = db.exists(digest)

To fetch data from the database use `get_data`:

.. code-block:: python

    data = db.get_data(digest)

To delete data from the database use `delete_data`:

.. code-block:: python

    data = db.delete_data(digest)

To query data from the database use `query_data`:

.. code-block:: python

    blobs = db.query_data(category='js')
