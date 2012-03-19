Introduction
============

twofactor is a proxy application that forces authentication
before anything is proxied.


Install
-------

using virtualenv::

    virtualenv twofactor
    cd twofactor
    git clone git://github.com/vangheem/twofactor.git
    cd twofactor
    ../bin/python setup.py develop
    ../bin/initializedb develop.ini
    ../bin/adduser development.ini --username=john@foo.bar
    ../bin/paster serve develop.ini
    ../bin/removeuser development.ini --username=john@foo.bar


Configuration
-------------
Must follow the example develop.ini provided.

Edit server and port settings for application server.



