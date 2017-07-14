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
#   - LDAPS (or no ldap, can disable certificate checkcs as well)
#   - STARTTLS (or not)
#   - simple bind (bind user DN and password)
#
# All this user finder does is connect, bind with an account that can search
# the specified base_dn, and then search for a _single_ result in which the
# given username matches the value of the username_attr on the object
#
# example values:
#   conn_string: ldaps://example.com
#   starttls: True
#   bind_dn: cn=test,ou=users,dc=example,dc=com
#   bind_pw: abc123
#   base_dn: ou=users,dc=example,dc=com
#   username_attr: mail
#   lookup_timeout: 60
class LDAPUserFinderPlugin(object):
    name = "LDAP Users"

    def __init__(self, conn_string, check_certificate, starttls, bind_dn, bind_pw, base_dn,
                 username_attr, lookup_timeout):
        self.conn_string = conn_string
        self.check_certificate = check_certificate.lower().strip() == "true"
        self.starttls = starttls.lower().strip() == "true"
        self.bind_dn = bind_dn
        self.bind_pw = bind_pw
        self.base_dn = base_dn
        self.username_attr = username_attr
        self.lookup_timeout = lookup_timeout

    @property
    def conn(self):
        if not self.check_certificate:
            ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

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

    def __call__(self, username):
        conn = self.conn
        if not conn:
            return False

        found = False
        try:
            userfilter = "({}={})".format(self.username_attr, username)
            results = conn.search_st(
                self.base_dn,
                ldap.SCOPE_SUBTREE,
                userfilter,
                attrlist=[self.username_attr])
            if len(results) > 0:
                if len(results) > 1:
                    logger.error("more than one user found with that username")
                else:
                    found = True
        except ldap.LDAPError as e:
            logger.error("LDAP error when performing user lookup")
            if type(e.message) == dict and e.message.has_key('desc'):
                logger.error(e.message['desc'])
            else:
                logger.error(e)

        # make sure the connection gets unbound
        #conn.unbind()

        return found

# LDAP User Finder is a WIP so disabled for now
if LDAP_AVAILABLE:
    addUserFinderPlugin(LDAPUserFinderPlugin)
