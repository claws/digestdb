''' Tests for digestdb.hashify '''

import os
import shutil
import tempfile

import unittest
import unittest.mock

import digestdb


SYS_TMP_DIR = os.environ.get('TMPDIR', tempfile.gettempdir())

# Some text to use in the test case
data = b'''Lorem ipsum dolor sit amet, consectetur adipisicing elit,
 sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad
 minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea
 commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit
 esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat
 cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est
 laborum.
'''


class HashTestCase(unittest.TestCase):

    def test_data_digest(self):
        ''' check data can be hashed into a digest '''

        with self.assertRaises(Exception) as cm:
            digestdb.hashify.data_digest('blah')
        expected = 'Invalid data type. Expected bytes but got'
        self.assertIn(expected, str(cm.exception))

        d = digestdb.hashify.data_digest(data)
        self.assertIsInstance(d, bytes)

    def test_file_digest(self):
        ''' check files can be hashed into a digest '''
        tempdir = tempfile.mkdtemp(dir=SYS_TMP_DIR)
        try:
            fd = tempfile.NamedTemporaryFile(dir=tempdir, delete=False)
            filename = fd.name
            fd.write(data)
            fd.flush()
            fd.close()

            d = digestdb.hashify.file_digest(filename)
            self.assertIsInstance(d, bytes)

        finally:
            if os.path.isdir(tempdir):
                shutil.rmtree(tempdir)

    def test_digest_filepath(self):
        ''' check filepath can be created from a digest '''

        digest = digestdb.hashify.data_digest(data)
        self.assertIsInstance(digest, bytes)

        with self.assertRaises(Exception) as cm:
            digestdb.hashify.digest_filepath(digest, dir_depth=0)
        expected = 'Invalid dir_depth. Value must be an'
        self.assertIn(expected, str(cm.exception))

        with self.assertRaises(Exception) as cm:
            digestdb.hashify.digest_filepath(digest, dir_depth='a')
        expected = 'Invalid dir_depth. Value must be an'
        self.assertIn(expected, str(cm.exception))

        for i in range(1, 10):
            fpath = digestdb.hashify.digest_filepath(digest, dir_depth=i)
            self.assertIsInstance(fpath, str)
            self.assertEqual(len(fpath.split(os.sep)), i + 1)
