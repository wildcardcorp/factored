Introduction
============

factored is a wsgi application that forces authentication
before is passed to the wsgi application.

This can also be used as a proxy for non-wsgi apps.


Install
-------

using virtualenv::

    virtualenv factored
    cd factored
    git clone git://github.com/vangheem/factored.git
    cd factored
    ../bin/python setup.py develop
    ../bin/initializedb develop.ini
    ../bin/adduser develop.ini --username=john@foo.bar
    ../bin/paster serve develop.ini
    ../bin/removeuser develop.ini --username=john@foo.bar


Configuration
-------------
Must follow the example develop.ini provided. You'll probably want to copy
that file into your own and change the settings.

Edit server and port settings for application server if not using with another
wsgi application.


Paste configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~

appname
    Appened to google auth keys so it doesn't overwrite others.
auth_tkt. prefixed options
    Configuration options that are passed directly into repoze.who's auth_tkt
    plugin.
auth_timeout
    The amount of time in seconds a normal authentication session is valid for.
auth_remember_timeout
    The amount of time in seconds the authentication seesion is valid for 
    when the user clicks "remember me."
base_auth_url
    Base url all authentication urls and resources are based off of. Useful if
    you're only looking to authenticate a portion of a site.
supported_auth_schemes
    Supported authentication schemes.
email_auth_window
    If using email authentication, the window of time the user has to enter
    correct code in.
email_auth.subject
    Email authencation subject used.
email_auth.sender
    Email authentication from address.
email_auth.body
    Email Authentication text body. `{code}` will be replaced with the code.
pyramid. prefixed options
    Configuration passed directly into pyramid configuration.
sqlalchemy.url
    Connection string for sql backend. Most configurations will work fine
    with normal sqlite.
mail. prefixed options
    Configuration passed directly to the mailer plugin. Options can be found at
    http://packages.python.org/pyramid_mailer/#configuration
autouserfinder
    Specify a plugin that will automatically find users for the system to allow
    authentication for. Pre-packaged plugins include `SQL` and `Email Domain`.
allowgooglecodereminder
    (true|false) value defaulting to false that allows the user, if the username
    is an email, to get a reminder of their code sent to them.
allowgooglecodereminder.subject
    If using allowing code reminders, the email subject of reminder
allowgooglecodereminder.sender
    If using allowing code reminders, the email from address of reminder
allowgooglecodereminder.body
    If using allowing code reminders, the email body of reminder


autouserfinder SQL configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

autouserfinder.connection_string
    sqlalchemy connection string to connection to the database.
autouserfinder.table_name
    Name of the table to lookup users in.
autouserfinder.email_field
    Name of the field to find the usernames(could be username or email field).


autouserfinder Email Domain configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

autouserfinder.valid_domains
    List of valid domains to automatically create users for.


Nginx Example Configuration
---------------------------
An example setup with nginx and load balancing::

    server {
        listen  80;
        server_name www.test.com;
        include proxy.conf;

        # paths to protect
        location ~ ^/admin.* {
            proxy_pass http://127.0.0.1:8000;
        }

        location / {
            proxy_pass http://app;
        }
    }

    server {
        listen 8090;
        include proxy.conf;
        location / {
            proxy_pass http://app;
        }
    }


Then factored would be configured to run on port 8000 and proxy
to 8090 and have `base_auth_url` url set to /admin/auth.


Sample Paste Configuration
--------------------------
An example to follow if you're not using a git checkout::

    [app:proxy]
    use = egg:factored#simpleproxy
    server = 127.0.0.1
    port = 8090

    [filter-app:main]
    use = egg:factored#main
    next = proxy
    appname = REPLACEME

    auth_tkt.secret = REPLACEME
    auth_tkt.cookie_name = factored
    auth_tkt.secure = false
    auth_tkt.include_ip = true

    auth_timeout = 7200
    auth_remember_timeout = 604800
    base_auth_url = /auth
    supported_auth_schemes = 
        Google Auth
        Email

    email_auth_window = 120
    # in seconds
    email_auth.subject = Authentication Request
    email_auth.sender = foo@bar.com
    email_auth.body = 
        You have requested authentication.
        Your temporary access code is: {code}

    autouserfinder = SQL
    autouserfinder.table_name = users
    autouserfinder.email_field = email
    autouserfinder.connection_string = sqlite:///%(here)s/users.db

    allowgooglecodereminder = true
    allowgooglecodereminder.subject = Authentication code reminder
    allowgooglecodereminder.sender = foo@bar.com
    allowgooglecodereminder.body = 
        You have requested code reminder.
        Your google auth code url is: {code}

    pyramid.reload_templates = true
    pyramid.debug_authorization = true
    pyramid.debug_notfound = true
    pyramid.debug_routematch = true
    pyramid.default_locale_name = en
    pyramid.includes =
        pyramid_tm
        pyramid_mailer

    sqlalchemy.url = sqlite:///%(here)s/test.db

    # all mail settings can be found at http://packages.python.org/pyramid_mailer/#configuration
    mail.host = localhost
    mail.port = 25

    [server:main]
    use = egg:Paste#http
    # Change to 0.0.0.0 to make public:
    host = 127.0.0.1
    port = 8000


With Gunicorn
-------------

Install::

    ../bin/easy_install gunicorn

to run::

    ../bin/gunicorn_paste --workers=2 develop.ini


TODO
----

- stayed logged in for `x` amount of seconds button configurable
