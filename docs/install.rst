Installation
============

Download
--------

Choose a release from `here <https://github.com/wildcardcorp/factored/releases>`_
or just download the latest::

    wget https://github.com/wildcardcorp/factored/archive/master.zip
    unzip factored-master
    mv factored-master factored


Or clone git for latest
-----------------------

from github::

    git clone git@github.com:wildcardcorp/factored.git


build
-----

The project uses buildout to manage dependencies::

    cd factored
    virtualenv .
    ./bin/python bootstrap.py
    ./bin/buildout


Test
----

with default sample config::

    ./bin/factored_initializedb develop.ini
    ./bin/pserve develop.ini

You should now have a factored server running on port 8000.


Using proxy
-----------

Install WSGIProxy::

    ./bin/easy_install WSGIProxy
