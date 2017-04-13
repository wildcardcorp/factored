from sqlalchemy import create_engine

import logging
logger = logging.getLogger(__name__)

# enable/disable LDAP user finder plugin
try:
    import ldap
    LDAP_AVAILABLE = True
except ImportError:
    logger.warning("python-ldap module not found, LDAPUserFinderPlugin "
                   "won't be enabled")
    LDAP_AVAILABLE = False




_finder_plugins = []


def addUserFinderPlugin(plugin):
    _finder_plugins.append(plugin)


def getUserFinderPlugins():
    return _finder_plugins


def getUserFinderPlugin(name):
    for plugin in _finder_plugins:
        if plugin.name == name:
            return plugin


class SQLUserFinder(object):
    """
    Auto find related item from a SQL database
    """
    name = "SQL"

    def __init__(self, table_name, email_field, connection_string):
        self.connection_string = connection_string
        self.table_name = table_name
        self.email_field = email_field

    @property
    def engine(self):
        return create_engine(self.connection_string)

    def __call__(self, username):
        select = 'select %s from %s where %s=?' % (
            self.email_field, self.table_name, self.email_field)
        engine = self.engine
        if engine.driver == 'mysqldb':
            select = select.replace('?', '%s')
        res = engine.execute(select, username)
        return len(res.fetchall()) > 0
addUserFinderPlugin(SQLUserFinder)


class EmailDomainFinderPlugin(object):
    name = "Email Domain"

    def __init__(self, valid_domains):
        from factored import app
        self.valid_domains = app._tolist(valid_domains)

    def __call__(self, email):
        email = email.lower()
        for valid in self.valid_domains:
            if email.endswith('@' + valid):
                return True
        return False
addUserFinderPlugin(EmailDomainFinderPlugin)



# Should handle:
#   - LDAPS
#   - STARTTLS
#   - simple bind (bind user DN and password)
#
# example values:
#   conn_string: ldaps://example.com
#   starttls: True
#   bind_dn: cn=test,ou=users,dc=example,dc=com
#   bind_pw: abc123
#   base_dn: ou=users,dc=example,dc=com
#   user_id_attr: sAMAccountName
#   lookup_timeout: 60
class LDAPUserFinderPlugin(object):
    name = "LDAP Users"

    def __init__(self, connstring, starttls, bind_dn, bind_pw, base_dn,
                 user_id_attr, lookup_timeout):
        self.conn_string = connstring
        self.starttls = starttls
        self.bind_dn = bind_dn
        self.bind_pw = bind_pw
        self.base_dn = base_dn
        self.user_id_attr = user_id_attr
        self.lookup_timeout = lookup_timeout

    @property
    def conn(self):
        conn = ldap.initialize(self.conn_string)
        if self.starttls:
            try:
                conn.start_tls_s()
            except ldap.LDAPError as e:
                logger.error("can't STARTTLS")
                if type(e.message) == dict and e.message.has_key("desc"):
                    logger.error(e.message['desc'])
                else:
                    logger.error(e)
                conn.unbind()
                return None
        try:
            conn.simple_bind_s(self.bind_dn, self.bind_pw)
        except ldap.INVALID_CREDENTIALS:
            logger.info("invalid credentials for bind dn: " + self.bind_dn)
            conn.unbind()
            return None
        except ldap.LDAPError as e:
            logger.error("LDAP error when binding")
            if type(e.message) == dict and e.message.has_key('desc'):
                logger.error(e.message['desc'])
            else:
                logger.error(e)
            conn.unbind()
            return None
        return conn

    def __call__(self, userid):
        conn = self.conn
        if not conn:
            return False

        found = False
        try:
            userfilter = "({}={})".format(self.user_id_attr, userid)
            results = conn.search_st(
                self.base_dn,
                ldap.SCOPE_SUBTREE,
                userfilter,
                attrs=[self.user_id_attr])
            if len(results) > 0:
                found = True
        except LDAPError as e:
            logger.error("LDAP error when performing user lookup")
            if type(e.message) == dict and e.message.has_key('desc'):
                logger.error(e.message['desc'])
            else:
                logger.error(e)

        # make sure the connection gets unbound
        #conn.unbind()

        return found

# LDAP User Finder is a WIP so disabled for now
#if LDAP_AVAILABLE:
#    addUserFinderPlugin(LDAPUserFinderPlugin)
