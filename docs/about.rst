Introduction
============

Factored is a comprehensive 2-factor authentication system that works with
any web technology.


Authorization Types
-------------------

Factored uses a plugin system to provide different types of authorizations. Out of
the box, it provides Google Authenticator and Email Token support.

Integration Strategies
----------------------

Factored supports different types of integrations for your web applications.

- Proxy: factor is in front of web application and sends authorized requests
  to configured web application.
- Web server plugins: Nginx and ATS plugins are avilable using lua.
- WSGI: A filter is provided to be use with Python Web Applications that
  utilize this standard.
