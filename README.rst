Introduction
============
Factored is a comprehensive 2-factor authentication system that works with any web technology. It intercepts the web request and makes sure the user does not see anything unless they first authenticate, seamless to any webapplication. It is compatible with NGINX, Apache Traffic Server and any app that uses LUA or WSGI.

`Read the docs <https://factored.readthedocs.org/en/latest/>`_

Credit
------
For implementation, customizations or the factored manager product that centralizes factored configuration, please contact us at https://wildcardcorp.com
info@wildcardcorp.com 
715.869.3440


.. image:: https://www.wildcardcorp.com/logo.png
   :height: 50
   :width: 382
   :alt: Original work by wildcardcorp.com
   :align: right
   



Notes on Requirements
---------------------

If you wish to use the LDAP auto user finder, then you need:

    * `python-ldap` python library
    * `libldap2-dev` system library
    * `libsasl2-dev` system library

If you wish to use sqlite (IE to get the default dev settings to work), then
you need:

    * `libsqlite3-dev` system library
