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
to 8090.

