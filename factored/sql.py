from sqlalchemy import engine_from_config
from factored.models import DBSession, User
from sqlalchemy import func
from factored.utils import generate_random_google_code


class DB(object):

    def __init__(self):
        pass

    def get_user(self, req, username):
        db = req.sm[req.registry.settings['db_session_id']]
        return db.query(User).filter(
            func.lower(User.username) == func.lower(username)).first()

    def create_user(self, req, username):
        db = req.sm[req.registry.settings['db_session_id']]
        secret = generate_random_google_code()
        user = User(username=username.lower(), secret=secret)
        db.add(user)
        return user

    def save(self, req, user):
        # not necessary here?
        pass


def factory(settings, app):
    engine = engine_from_config(settings, 'sqlalchemy.')
    configure_db = settings.pop('configure_db', 'true').lower() == 'true'

    if configure_db:
        DBSession.configure(bind=engine)
        db_session_id = 'f'
    else:
        # why would you do this?
        # well... if you have multiple factored wsgi instances running
        # this allows you to change between the connection objects
        db_session_id = settings.pop('db_session_id')
    return db_session_id, DB()
