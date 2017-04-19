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


Apache Traffic Server (ATS) Plugin
----------------------------------

Requirements
~~~~~~~~~~~~

- ATS 7.2.x (tested on 7.2.0) configured as a reverse proxy server
- ATS Lua plugin

See the `Apache Traffic Server Documentation <https://docs.trafficserver.apache.org/en/latest/index.html>`_
for how to install and configure it. Take note that you will need to use a version of
ATS compiled with the `--enable-experimental-plugins`, or you will need to configure
your installation to work with the `TS-Lua <https://github.com/portl4t/ts-lua>`_ plugin.


Install
~~~~~~~

Put the following into a file that is readable by ATS (ex:
``/etc/factored/plugin.lua``):::

    --
    --  These should match your factored settings (IE the values in your INI
    --  configuration file). This value SHOULD be called "factored_settings".
    --
    factored_settings = {
      -- the HOST and PORT Factored is running on
      scheme='http',
      host='127.0.0.1',
      port=8000,

      -- AUTH TKT settings
      cookie_name='your_auth_tkt_cookie_name',
      secret='your_auth_tkt_secret_here',
      include_ip=false, -- [true] to include IP in cookie value
      timeout=false, -- [true] to manually handle cookie timeouts

      -- PLUGIN directory -- by default factored has a "plugins" directory
      -- which contains several lua files that are necessary. This directory
      -- should contain "ats.lua", "factored.lua", "bit.lua", and "sha.lua"
      basepath='/path/to/factored/plugins/'
    }

    ------------------------------------------------------------------------------
    -- ## PAST THIS POINT YOU SHOULDN'T NEED TO MODIFY ###########################
    -- (but it is required)
    --
    require 'package'
    if string.find(package.path, factored_settings.basepath) == nil then
        ts.add_package_path(factored_settings.basepath .. '?.lua')
    end
    ats = require 'ats'

    function do_remap()
      ts.http.set_debug(0)
      local status, ret = pcall(ats.do_remap)
      -- if the pcall was successful, then we should be able to return
      -- the result of the pcall 
      if status then
        return ret
      else
        -- this is a special case, if something went wrong in the normal
        -- remap process, the url will be intercepted with a 403 message
        -- if you want a customized message, put your own intercept function here
        ts.http.intercept(ats.factored_failed) 
        return 0
      end
    end

Then in your ATS ``remap.config`` file, you'll want a line like the
following:::

    map TARGET REPLACEMENT @plugin=/path/to/tslua.so @pparam=/path/to/your/custom/settings.lua

Where 'TARGET' would be the incoming URL and 'REPLACEMENT' is the upstream
(NOT the factored server, but whichever URL you want behind factored).

The ``/path/to/tslua.so`` is going to be based on your installation -- a
default ATS installation from source on Ubuntu will put it in
``/usr/local/libexec/tslua.so``. Note -- the full path is necessary.

The ``/path/to/your/custom/settings.lua`` would be the path to the file
that contains your customized factored configuration
(``/etc/factored/plugin.lua`` from the example above). Note -- the full path is
necessary.

This plugin works by checking the auth_tkt cookie on each request -- if there
is a cookie, and it's valid, then the plugin just passes on factored entirely,
letting ATS continue with the request process. If the cookie is not found or
not valid, the plugin will re-write the upstream to point at the configured
factored server.
