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
    ../bin/adduser development.ini --username=john@foo.bar
    ../bin/paster serve develop.ini
    ../bin/removeuser development.ini --username=john@foo.bar


Configuration
-------------
Must follow the example develop.ini provided.

Edit server and port settings for application server.



