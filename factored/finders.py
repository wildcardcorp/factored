from sqlalchemy import create_engine


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
        select = 'select %s from %s where %s=?' % (self.email_field,
            self.table_name, self.email_field)
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
        for valid in self.valid_domains:
            if email.endswith('@' + valid):
                return True
        return False
addUserFinderPlugin(EmailDomainFinderPlugin)
