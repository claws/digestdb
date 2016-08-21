Quickstart
==========


Database
--------

To start using the DigestDB you first need to create a database. Let's create
a :class:`DigestDB` and we'll tell it to use the current directory for storing
any binary content.

.. code-block:: python

    from digestdb import DigestDB

    db = DigestDB('.')

By default the :class:`DigestDB` will create a file called ``digestdb.db``
and a directory called ``digestdb.data``. The `digestdb.db` is a simple SQLite
database that stores the categories and digests of the blobs. Categories
are used to group binary content to facilitate searching (e.g. JavaScript,
css, images, etc). The ``digestdb.data`` directory is the top level directory
in which all the binary blobs are stored.

When the :class:`DigestDB` is instantiated it checks for a lock file. The
lock file ensure that it has exclusive access to the data otherwise there is
a risk of losing synchronisation between the files on disk and those listing
in the database. If the :class:`DigestDB` encounters a lock file when starting
up it will report the error and shut down.

Before writing or reading data from the :class:`DigestDB` it must first be
opened.

.. code-block:: python

    db.open()

Conversely, when you are finished with the database it must be closed.

.. code-block:: python

    db.close()

If you re-open the database it will simply continue on from where it left off.

If you want to create a new database you can explicitly specify ``filename``
and ``data_dir``.

The :class:`DigestDB` takes a number of optional arguments. The
``dir_depth`` is one of the most important settings and is disucssed in detail
in the following section.


Database Depth
++++++++++++++

To understand the database directory depth we need some background first.

There isn't any real limit on the number of files that can be stored in a
directory. However, it can become very slow as the number of files increases.
The time it takes to list and check for the existance of a file increases
as the number of files increase. So we need a strategy to balance the files
over some number of direcotries to avoid this problem.

The file path that determines where a blob is stored will be created from the
blob's hash. As a new item is added to the database a hash (SHA-256 by
default) is calculated. The default :class:`DigestDB` ``dir_depth`` is 3. This
means that the first three bytes from the hash digest are used to construct
the directory structure.

Given the following hash:

.. code-block:: console

        8fdd8b7dfa0d7d4f761da78e76d62ec4bee3b1847a6ad48507090e13752b2d

A ``dir_depth`` of 1 would result in the data item being stored in the
following locaiton:

.. code-block:: console

        8f/8fdd8b7dfa0d7d4f761da78e76d62ec4bee3b1847a6ad48507090e13752b2d

A ``dir_depth`` of 3 would result in the data item being stored in the
following locaiton:

.. code-block:: console

        8f/dd/8b/8fdd8b7dfa0d7d4f761da78e76d62ec4bee3b1847a6ad48507090e13752b2d

Each directory level adds 256 directories (\x00, \x01, ... \xfe, \xff). So
with a directory depth of 1 we get 256 directories. With a depth of 2 we get
256 * 256 = 65536 and with a depth of 3 we get 256 * 256 * 256 = 16,777,216
directories.

The chosen directory depth can significantly impact cleanup operations.
Let's assume a naive internal implementation that creates all directories up
front. Without storing any data files at all and a ``depth=1`` it takes about
0.03 seconds. When ``depth=2`` it takes about 10 seconds to remove the 65
thousand directories. When ``depth=3`` it takes a very long time (2441 secs)
to remove the 16 million directories.

For this reason, directories are created only when required. This
significantly reduces the time it takes to remove transient databases, such
as those used in unit tests.

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
signed integer is 2,147,483,647. So let's bump the expected file items up to
2 billion.

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

Categories provide a method to group associated data items in the database.
This provides a mechansim for more efficient querying of data by category.

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

Binary data can be stored, retrieved and queried.

To add a binary blob to the database use ``put_data``:

.. code-block:: python

    digest = db.put_data('js', b'\x00\x01...')

To add the contents of a file to the database use ``put_file``:

.. code-block:: python

    digest = db.put_file('js', '/path/to/js/file')

To check if data exists in the database use ``exists``:

.. code-block:: python

    data = db.exists(digest)

To fetch data from the database use ``get_data``:

.. code-block:: python

    data = db.get_data(digest)

To delete data from the database use ``delete_data``:

.. code-block:: python

    data = db.delete_data(digest)

To query data from the database use ``query_data``:

.. code-block:: python

    blobs = db.query_data(category='js')
