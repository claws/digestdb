''' Tests for digestdb.database '''

import datetime
import os
import random
import shutil
import tempfile

import unittest
import unittest.mock

import digestdb


SYS_TMP_DIR = os.environ.get('TMPDIR', tempfile.gettempdir())


# Some text to use in the test case
data = b'\x03\xee\x02\x00\x07\x00\x00\x00\x0c\x00\x00\x00'


def create_data_item(categories, max_size=1000, timestamp=False):
    ''' Create an item representing a data item '''
    item_size = random.randint(20, max_size)
    cat = random.choice(categories)
    data = b''.join(
        random.randint(1, 255).to_bytes(1, byteorder='little')
        for i in range(item_size))
    ts = None
    if timestamp:
        ts = datetime.datetime.now()
    return cat, data, ts


class DigestDBTestCase(unittest.TestCase):

    def test_database_db_dir(self):
        ''' check data can be hashed into a digest '''

        with self.assertRaises(Exception) as cm:
            digestdb.DigestDB('blah')
        expected = 'Invalid db_dir:'
        self.assertIn(expected, str(cm.exception))

        tempdir = tempfile.mkdtemp(dir=SYS_TMP_DIR)
        try:
            digestdb.DigestDB(tempdir)
        finally:
            if os.path.isdir(tempdir):
                shutil.rmtree(tempdir)

    def test_database_locking(self):
        ''' check that database locking works '''
        tempdir = tempfile.mkdtemp(dir=SYS_TMP_DIR)
        try:
            db1 = digestdb.DigestDB(tempdir)
            self.assertFalse(os.path.exists(db1.lock_file))
            db1.open()
            self.assertTrue(os.path.exists(db1.lock_file))

            # attempt to open another db. It should detect the lock file
            # and raise an exception.
            db2 = digestdb.DigestDB(tempdir)
            with self.assertRaises(Exception) as cm:
                db2.open()
            expected = 'Database is already open'
            self.assertIn(expected, str(cm.exception))

            # close the first database, which should remove lock file
            db1.close()
            self.assertFalse(os.path.exists(db1.lock_file))

            # Now try to open second db again. The lock file created
            # by db1 should be gone, expect no exceptions.
            db2.open()
            self.assertTrue(os.path.exists(db1.lock_file))
            db2.close()
            self.assertFalse(os.path.exists(db1.lock_file))

        finally:
            if os.path.isdir(tempdir):
                shutil.rmtree(tempdir)

    def test_database_categories(self):
        ''' check categories can be added, retrieved and queried '''
        tempdir = tempfile.mkdtemp(dir=SYS_TMP_DIR)

        clabel = 'test'
        cdesc = 'This category is just for tests'

        try:
            db = digestdb.DigestDB(tempdir, dir_depth=1)
            db.open()

            db.query_category()

            with self.assertRaises(Exception) as cm:
                db.get_category(clabel)
            expected = 'Category {} not found in database'.format(clabel)
            self.assertIn(expected, str(cm.exception))

            db.put_category(clabel, cdesc)
            db.query_category(label=clabel)

            l_out, d_out = db.get_category(clabel)
            self.assertEqual(l_out, clabel)
            self.assertEqual(d_out, cdesc)

            matches = db.query_category(label=clabel)
            self.assertEqual(len(matches), 1)

            matches = db.query_category(description='just for')
            self.assertEqual(len(matches), 1)

            db.close()

        finally:
            if os.path.isdir(tempdir):
                shutil.rmtree(tempdir)

    def test_database_blobs(self):
        ''' check blobs can be added, retrieved and queried '''
        tempdir = tempfile.mkdtemp(dir=SYS_TMP_DIR)

        try:
            dir_depth = 1
            db = digestdb.DigestDB(tempdir, dir_depth=dir_depth)
            db.open()

            # add some categories to use when adding blobs
            cat1 = 'cat1'
            cat2 = 'cat2'
            categories = (cat1, cat2)
            for cat in categories:
                db.put_category(cat)
            self.assertEqual(db.count_category(), 2)

            # Add 4 items individually
            test_data = {}
            for i in range(4):
                cat, data, ts = create_data_item(categories)
                digest = db.put_data(cat, data, ts)
                test_data[digest] = (cat, data, ts)
            self.assertEqual(len(test_data), 4)

            # Choose one of the test items and check that it exists in
            # the database, then fetch it back and check its contents.
            digest = random.choice(list(test_data))
            data_in = test_data[digest][1]
            self.assertTrue(db.exists(digest))
            self.assertEqual(data_in, db.get_data(digest))

            # Check that many data items can be added using a single call
            test_items = [create_data_item(categories) for i in range(10)]
            digests = db.put_data_many(*test_items)
            self.assertEqual(len(digests), 10)

            # Check that data queries can be performed based on category
            cat1_matches = db.query_data(category=cat1)
            cat2_matches = db.query_data(category=cat2)
            total_matches = len(cat1_matches) + len(cat2_matches)
            # 14 items were added in this test
            self.assertEqual(total_matches, 14)
            self.assertEqual(db.count_data(), 14)

            db.delete_data(digest)
            self.assertFalse(db.exists(digest))

            # deleting the same item again should not cause an error
            db.delete_data(digest)

            db.close()

        finally:
            if os.path.isdir(tempdir):
                shutil.rmtree(tempdir)

    def test_database_files(self):
        ''' check files can be added, retrieved and queried '''
        tempdir = tempfile.mkdtemp(dir=SYS_TMP_DIR)

        try:
            dir_depth = 1
            db = digestdb.DigestDB(tempdir, dir_depth=dir_depth)
            db.open()

            # add some categories to use when adding blobs
            cat1 = 'cat1'
            cat2 = 'cat2'
            categories = (cat1, cat2)
            for cat in categories:
                db.put_category(cat)
            self.assertEqual(db.count_category(), 2)

            # Add 4 items individually
            test_data = {}
            for i in range(4):
                cat, data, ts = create_data_item(categories)
                filepath = os.path.join(tempdir, 'tmp_file_{}'.format(i))
                with open(filepath, 'wb') as fd:
                    fd.write(data)
                digest = db.put_file(cat, filepath, ts)
                test_data[digest] = (cat, filepath, ts)
            self.assertEqual(len(test_data), 4)

            # Choose one of the test items and check that it exists in
            # the database, then fetch it back and check its contents.
            digest = random.choice(list(test_data))
            filepath = test_data[digest][1]
            self.assertTrue(db.exists(digest))
            with open(filepath, 'rb') as fd:
                file_data = fd.read()
            self.assertEqual(file_data, db.get_data(digest))

            self.assertFalse(db.exists(b'deadbeef'))

            # Check that data queries can be performed based on category
            cat1_matches = db.query_data(category=cat1)
            cat2_matches = db.query_data(category=cat2)
            total_matches = len(cat1_matches) + len(cat2_matches)
            # 4 items were added in this test
            self.assertEqual(total_matches, 4)
            self.assertEqual(db.count_data(), 4)

            db.delete_data(digest)
            self.assertEqual(db.count_data(), 3)
            self.assertFalse(db.exists(digest))

            # deleting the same item again should not cause an error
            db.delete_data(digest)

            db.close()

        finally:
            if os.path.isdir(tempdir):
                shutil.rmtree(tempdir)
