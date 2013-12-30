from sqlalchemy.exc import InterfaceError

key = 'SM'
skey = 'SM.sessions'

_registered_session_factories = {}


def registerSession(name, Session):
    _registered_session_factories[name] = Session


def getSessionManager(environ):
    return environ[key]


class SM(object):

    def __init__(self, environ):
        self.environ = environ
        if skey not in environ:
            environ[skey] = {}
        self.sessions = environ[skey]

    def __getattr__(self, name):
        if name not in _registered_session_factories:
            raise AttributeError
        if name not in self.sessions:
            self.sessions[name] = _registered_session_factories[name]()
        return self.sessions[name]

    __getitem__ = __getattr__

    def commit(self):
        for session in self.sessions.values():
            session.commit()

    def rollback(self):
        for session in self.sessions.values():
            try:
                session.rollback()
            except InterfaceError:
                pass

    def close(self):
        for session in self.sessions.values():
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
