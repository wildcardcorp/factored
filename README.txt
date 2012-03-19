Introduction
============

twofactor is a proxy application that forces authentication
before anything is proxied.


Install
-------

using virtualenv::

    virtualenv twofactor
    cd twofactor
    svn checkout twofactor
    cd twofactor
    ../bin/python setup.py develop
    ../bin/initializedb develop.ini
    ../bin/adduser development.ini
    ../bin/paster serve develop.ini


Configuration
-------------
Must follow the example develop.ini provided.

Edit server and port settings for application server.


