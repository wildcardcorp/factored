Web Server Plugins
==================

factored offers to web server plugins: nginx and apache traffic server. Both
plugins require the web server to be compile with lua support.


Nginx
-----

Requirements
~~~~~~~~~~~~

- lua 5.1 and dev packages
- nginx compiled with http://wiki.nginx.org/HttpLuaModule
- requires using sha256 auth_tkt hash algorithm


Example Config
~~~~~~~~~~~~~~

You'll need to customize this::

    location / {
          # Thes must match factored config
          set $fcookie_name 'pnutbtr';
          set $fsecret 'secret';
          set $finclude_ip 0;
          set $ftimeout 0;

          set $authenticated 0;
          set $path '';
          set $proxyto '127.0.0.1:8000/';
          set_by_lua_file $authenticated /path/to/installed/factored/plugins/nginx.lua;
          if ($authenticated = 1) {
            set $proxyto '127.0.0.1:8080/';
            set $path 'VirtualHostBase/http/www.foobar.com:80/Plone/VirtualHostRoot/';
          }

          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_pass http://$proxyto/$path$request_uri;
        }


Apache Traffic Server Plugin
----------------------------


Requirements
~~~~~~~~~~~~

- lua 5.1 and dev packages
- ats compiled with --enable-experimental-plugins
- requires using sha256 auth_tkt hash algorithm


Install
~~~~~~~

- copy ats plugin directory to where you want to configure it
- configure plugin directory/factored.lua settings to match factored settings
- Finally, in your remap config, use something like::

    map http://www.foobar.com/ http://127.0.0.1:8080/ @plugin=lua.so @pparam=/path/to/ats/plugin/factored.lua
