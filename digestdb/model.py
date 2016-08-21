''' This module defines the database schema used in the database '''

import datetime
import logging

from sqlalchemy.ext.declarative import as_declarative  # declarative_base
from sqlalchemy import (
    LargeBinary,
    Column,
    DateTime,
    Integer,
    String,
    ForeignKey)


logger = logging.getLogger(__name__)


# _Base = declarative_base()

@as_declarative()
class Base(object):
    ''' An abstract base class providing common table functions '''

    __abstract__ = True

    def __str__(self):
        return "<{} ({})>".format(
            self.__class__.__name__, self.to_dict())

    def to_dict(self):
        return {
            col.name: getattr(self, col.name)
            for col in self.__table__.columns}


class Category(Base):
    '''
    This table definition stores category identifiers.

    Category identifiers are used to categorise the different classes of
    objects stored in the database. Here are some examples of how categories
    can be used to group different kinds of blobs:

    - when storing inter-process messages (e.g. for later analysis or replay)
      the categories might be the message kinds or identifiers.
    - when storing web requests the catoegories might be route paths.
    - when storing web server resources the categories might represent
      images, css, javascript, etc.
    '''

    __tablename__ = 'categories'

    label = Column(String, primary_key=True)

    description = Column(String)


class Digest(Base):
    '''
    This table definition stores a timestamp, object identifier and the hash
    for a binary blob.
    '''

    __tablename__ = 'digests'

    digest = Column(LargeBinary, primary_key=True)

    category_label = Column(String, ForeignKey('categories.label'))

    timestamp = Column(DateTime, default=datetime.datetime.now)

    byte_size = Column(Integer)
