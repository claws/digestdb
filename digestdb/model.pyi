from sqlalchemy import Column, DateTime, Integer, LargeBinary, String
from sqlalchemy.schema import MetaData
class Base:
  metadata = None  # type: MetaData
  def __init__(self, *args, **kwargs) -> None: ...
class Category(Base):
    label = Column(String, primary_key=True)
    description = Column(String)
class Digest(Base):
    digest = Column(LargeBinary, primary_key=True)
    category_label = Column(String)
    timestamp = Column(DateTime)
    byte_size = Column(Integer)
