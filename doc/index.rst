DigestDB
========

Digestdb provides database style (e.g. SQL) access to binary data files
stored in a balanced set of file system directories.

Digestdb aims to provide an efficient strategy for storing and serving
lots of binary files while maintaining a high level of performance.

DigestDB was developed specifically for scenarios that required storing and
recalling large numbers of large (~100K - ~40MB) binary blobs.

A pure database solution did not seem to be the right choice for the storing
lots of binary data. The file system works just fine for storing and accessing
data files. Digestdb blends the two approaches to provide database style
access to binary files store on the local file system.

DigestDB is internally comprised of two parts:

  - a SQLite database that stores blob categories and the SHA-256 hashes of
    binary blobs.

  - a filesystem directory structure for storing the binary blobs in
    filenames that match the hash digest of the blob.

DigestDB is written using Python 3.5 and is licensed under the MPL license.


.. toctree::
   :maxdepth: 1
   :numbered:

   user/index
   api/index
   dev/index
