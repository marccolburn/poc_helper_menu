from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()
engine = create_engine('sqlite:///poc_helper.db')
Session = sessionmaker(bind=engine)
session = Session()

class Lab(Base):
    __tablename__ = 'labs'
    id = Column(Integer, primary_key=True)
    lab_name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    lab_type = Column(String, default='containerlab', nullable=False)
    remote_containerlab_host = Column(String, nullable=True) 
    remote_containerlab_username = Column(String, nullable=True)
    containerlab_name = Column(String, nullable=True)  # Used for containerlab prefix
    topology_path = Column(String, nullable=True) 

    # Relationships
    hosts = relationship("Host", back_populates="lab")
    links = relationship("Link", back_populates="lab")

class Host(Base):
    __tablename__ = 'hosts'
    id = Column(Integer, primary_key=True)
    hostname = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    network_os = Column(String, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    image_type = Column(String, nullable=False)
    lab_name = Column(String, ForeignKey('labs.lab_name'), nullable=False)
    console = Column(String, nullable=True)  # Console connection address
    
    # Relationship
    lab = relationship("Lab", back_populates="hosts")

class Link(Base):
    __tablename__ = 'links'
    id = Column(Integer, primary_key=True)
    source_host = Column(String, nullable=False)
    source_interface = Column(String, nullable=False)
    destination_host = Column(String, nullable=False)
    destination_interface = Column(String, nullable=False)
    jitter = Column(Integer, default=0, nullable=False)
    latency = Column(Integer, default=0, nullable=False)
    loss = Column(Integer, default=0, nullable=False)
    rate = Column(Integer, default=0, nullable=False)
    corruption = Column(Integer, default=0, nullable=False)
    state = Column(String, default='enabled', nullable=False)
    lab_name = Column(String, ForeignKey('labs.lab_name'), nullable=False)
    
    # Relationship
    lab = relationship("Lab", back_populates="links")

Base.metadata.create_all(engine)
