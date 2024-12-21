from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine('sqlite:///poc_helper.db')
Session = sessionmaker(bind=engine)
session = Session()

class Host(Base):
    __tablename__ = 'hosts'
    id = Column(Integer, primary_key=True)
    hostname = Column(String, unique=True, nullable=False)
    ip_address = Column(String, nullable=False)
    network_os = Column(String, nullable=False)
    connection = Column(String, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    image_type = Column(String, nullable=False)

class Link(Base):
    __tablename__ = 'links'
    id = Column(Integer, primary_key=True)
    source_host = Column(String, nullable=False)
    source_interface = Column(String, nullable=False)
    destination_host = Column(String, nullable=False)
    destination_interface = Column(String, nullable=False)

Base.metadata.create_all(engine)
