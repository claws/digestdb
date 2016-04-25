Blobdb
======

Blobdb is a database for storing binary data in a balanced set of file
system directories and providing access to this data via tradiational
database style (e.g. SQL) access. Blobdb aims to provide an efficient strategy
for storing and serving lots of binary files while maintaining a high level of
performance.

A pure database solution did not seem to be the right choice for the storing
the binary data. Prior database based implementations were unimpressively slow.

The file system typically works just fine for storing and accessing data files.
However, we also needed some querying capabilities. Hence we have ended up with a
blend of the two.

Blobdb was developed specifically for scenarios that required storing and
recalling large numbers of large (~100K - ~40MB) binary blobs.

Blobdb is internally comprised of two parts:

  - the database that stores blob categories and the SHA-256 hashes of binary
    blobs.

  - a filesystem directory structure for storing the binary blobs in
    filenames that match the hash digest of the blob.

Blobdb is written using Python 3.5 and is licensed under the MPL license.

Blobdb is in the early stages of development.


.. toctree::
   :maxdepth: 1
   :numbered:

   user/index
   api/index
