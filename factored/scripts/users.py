import transaction
import argparse

from sqlalchemy import engine_from_config

from pyramid.paster import get_appsettings, setup_logging
from factored.models import DBSession, User
from factored.utils import get_barcode_image
from factored.utils import create_user


addparser = argparse.ArgumentParser(description='Add user')
addparser.add_argument('config', help='configuration file')
addparser.add_argument('--username', dest='username', help='username')


def add():
    arguments = addparser.parse_args()
    if not arguments.config or not arguments.username:
        addparser.print_usage()
    else:
        config_uri = arguments.config
        setup_logging(config_uri)
        settings = get_appsettings(config_uri)
        engine = engine_from_config(settings, 'sqlalchemy.')
        DBSession.configure(bind=engine)
        with transaction.manager:
            username = arguments.username
            user = create_user(username)
            print 'barcode url:', get_barcode_image(username, user.secret)
            print 'secret:', user.secret

removeparser = argparse.ArgumentParser(description='Remove user')
removeparser.add_argument('config', help='configuration file')
removeparser.add_argument('--username', dest='username', help='username')


def remove():
    arguments = removeparser.parse_args()
    if not arguments.config or not arguments.username:
        removeparser.print_usage()
    else:
        config_uri = arguments.config
        setup_logging(config_uri)
        settings = get_appsettings(config_uri)
        engine = engine_from_config(settings, 'sqlalchemy.')
        DBSession.configure(bind=engine)
        with transaction.manager:
            user = DBSession.query(User).filter_by(
                username=arguments.username).all()
            if len(user) > 0:
                DBSession.delete(user[0])
            else:
                print '"%s" user not found' % arguments.username

listparser = argparse.ArgumentParser(description='Remove user')
listparser.add_argument('config', help='configuration file')


def listusers():
    arguments = removeparser.parse_args()
    if not arguments.config:
        removeparser.print_usage()
    else:
        config_uri = arguments.config
        setup_logging(config_uri)
        settings = get_appsettings(config_uri)
        engine = engine_from_config(settings, 'sqlalchemy.')
        DBSession.configure(bind=engine)
        with transaction.manager:
            for user in DBSession.query(User).all():
                print user.username


listuserparser = argparse.ArgumentParser(description='List user info')
listuserparser.add_argument('config', help='configuration file')
listuserparser.add_argument('--username', dest='username', help='username')


def listuserinfo():
    arguments = listuserparser.parse_args()
    if not arguments.config or not arguments.username:
        listuserparser.print_usage()
    else:
        config_uri = arguments.config
        setup_logging(config_uri)
        settings = get_appsettings(config_uri)
        engine = engine_from_config(settings, 'sqlalchemy.')
        DBSession.configure(bind=engine)
        with transaction.manager:
            users = DBSession.query(User).filter_by(
                username=arguments.username).all()
            if len(users) > 0:
                user = users[0]
                print 'username:%s, secret: %s' % (
                    user.username, user.secret)
                print 'bar code url:', get_barcode_image(user.username,
                                                         user.secret)
            else:
                print '"%s" user not found' % arguments.username
