Apache Traffic Server Plugin
============================


Requirements
------------

- lua 5.1 and dev packages
- ats compiled with enable-experimental-plugins
- requires using sha256 auth_tkt


Install
-------

- copy ats plugin directory to where you want to configure it
- configure plugin directory/factored.lua settings to match factored settings
- map http://www.foobar.com/ http://127.0.0.1:8080/ @plugin=lua.so @pparam=/path/to/ats/plugin/factored.lua


TODO
----

- change to one plugin installation location and use a small settings file to load plugin
    - should allow for multiple configurations easier
- also could use some way to easier configure multiple factored configurations
  for different websites

