from sqlalchemy import (
    engine_from_config,
    Column,
    Integer,
    String,
    Float)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from factored.plugins import IDataStorePlugin


Base = declarative_base()
DBSession = scoped_session(sessionmaker())


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id = Column(Integer, primary_key=True)
    host = Column(String)
    subject = Column(String)
    timestamp = Column(Float)
    payload = Column(String)

    def __repr__(self):
        return "<AccessRequest [{}] ({}) {} {}>".format(
            self.id,
            self.host,
            self.subject, 
            self.timestamp)


class SQLDataStore(IDataStorePlugin):
    def initialize(self, settings):
        self.dbengine = engine_from_config(settings, prefix="sql.")
        DBSession.configure(bind=self.dbengine)
        self.dbsession = DBSession()

        # make sure tables are created
        Base.metadata.create_all(self.dbengine)

    def store_access_request(self, host, subject, timestamp, payload):
        self.delete_access_requests(host, subject)

        ar = AccessRequest()
        ar.host = host
        ar.subject = subject
        ar.timestamp = timestamp
        ar.payload = payload

        db = self.dbsession
        db.add(ar)
        db.commit()

    def get_access_request(self, host, subject):
        db = self.dbsession
        ar = db.query(AccessRequest).filter_by(host=host, subject=subject).first()
        if ar is None:
            return None
        return (ar.host, ar.subject, ar.timestamp, ar.payload)

    def delete_access_requests(self, host, subject):
        db = self.dbsession
        db.query(AccessRequest).filter_by(host=host, subject=subject).delete()
        db.commit()
