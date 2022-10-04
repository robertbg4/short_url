from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.schema import Column
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.sql.sqltypes import DateTime, Integer, String

engine = create_engine(
    'postgresql://r.r.rakhmatullin:password@localhost:5432/work', echo=True, future=True
)

Base = declarative_base()


class Links(Base):
    __tablename__ = 'links'
    __table_args__ = {'schema': 'short'}

    code = Column(String, primary_key=True)
    original_url = Column(String, nullable=True)
    transitions = relationship('Transitions', back_populates='link', cascade='all, delete', passive_deletes=True)


class Transitions(Base):
    __tablename__ = 'transitions'
    __table_args__ = {'schema': 'short'}

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.now())
    link_code = Column(String, ForeignKey('short.links.code', ondelete='CASCADE'), nullable=False)

    link = relationship('Links', back_populates='transitions')


Base.metadata.create_all(engine)
