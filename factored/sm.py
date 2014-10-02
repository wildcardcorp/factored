from sqlalchemy.exc import InterfaceError
import threading


_local = threading.local()

key = 'SM'
skey = 'SM.sessions'

_registered_sessions = {}


def _getRegisteredSessions():
    return _registered_sessions
    #if not hasattr(_local, 'data'):
    #    _local.data = {}
    #return _local.data


def registerSession(name, Session):
    _getRegisteredSessions()[name] = Session


def getSessionManager(environ):
    return environ[key]


class SM(object):
    """
    yes, I know this is sort of wonky...

    Sooo.. what's the point?

    Well, I have apps that I write which have multiple factored instances
    and I need a way to make them all our together okay.

    So this allows me to jungle the different app sessions.
    """

    def __init__(self, environ):
        self.environ = environ
        if skey not in environ:
            environ[skey] = {}
        self.sessions = environ[skey]

    def __getattr__(self, name):
        if name not in _getRegisteredSessions():
            raise AttributeError
        if name not in self.sessions:
            session = _getRegisteredSessions()[name]
            if callable(session):
                session = session()
            self.sessions[name] = session
        return self.sessions[name]

    __getitem__ = __getattr__

    def commit(self):
        for session in self.sessions.values():
            if hasattr(session, 'commit'):
                session.commit()

    def rollback(self):
        for session in self.sessions.values():
            try:
                if hasattr(session, 'rollback'):
                    session.rollback()
            except InterfaceError:
                pass

    def close(self):
        for session in self.sessions.values():
            if hasattr('session', 'close'):
                session.close()


class SMFilter(object):
    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):
        if key not in environ:
            environ[key] = SM(environ)
        sm = environ[key]

        try:
            result = self.application(environ, start_response)
            sm.commit()
        except:
            sm.rollback()
            raise

        sm.close()
        if key in environ:
            del environ[key]
        if skey in environ:
            del environ[skey]
        return result


def make_sm(app, global_conf):
    return SMFilter(app)
