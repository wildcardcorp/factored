--[[
--  These settings should match with your factored settings.
--
--  Put these in a file on a path that ATS can read from, then modify the
--  ATS remap config to have a line similar to:
--
--      map X Y @plugin=/path/to/tslua.so @pparam=/path/to/your/custom/settings.lua
--
--  See the documentation for more detailed info.
--
--  Below is an example config file:

--
--  These should match your factored settings (IE the values in your INI
--  configuration file). This value SHOULD be called "factored_settings".
--
factored_settings = {
  -- the HOST and PORT Factored is running on
  host='127.0.0.1',
  port=8000,

  -- AUTH TKT settings
  cookie_name='pnutbtr',
  secret='secret',
  include_ip=false, -- [true] to include IP in cookie value
  timeout=false, -- [true] to manually handle cookie timeouts

  -- PLUGIN directory -- by default factored has a "plugins" directory
  -- which contains several lua files that are necessary. This directory
  -- should contain "ats.lua", "factored.lua", "bit.lua", and "sha.lua"
  basepath='/opt/factored/src/plugins/'
}

-- this needs to be in your custom settings file, and probably doesn't
-- need to be modified.
require 'package'
if string.find(package.path, factored_settings.basepath) == nil then
    ts.add_package_path(factored_settings.basepath .. '?.lua')
end
require 'ats'

--]]


require 'string'
require 'math'
require 'package'
require 'os'

if string.find(package.path, factored_settings.basepath) == nil then
    ts.add_package_path(factored_settings.basepath .. '?.lua')
end
require 'factored'


-- these are used to "cache" client request values so they can be used to
-- communicate correctly with factored through HTTP headers
local pristine_scheme = ''
local pristine_host = ''
local pristine_port = ''


--
-- modify the request sent to the upstream server to reset the headers used
-- by Factored to generate proper URL's for it's internal use
--
function send_request()
    ts.server_request.header['X-Forwarded-Protocol'] = pristine_scheme
    final_host = pristine_host
    -- only add the port if it's non-standard. It would make ugly url's,
    -- and likely urls that are not expected otherwise
    if pristine_port ~= '80' and pristine_port ~= '443' then
        final_host = final_host .. ':' .. pristine_port
    end
    ts.server_request.header['Host'] = final_host
end

--
-- verify the AUTH TKT cookie is valid, and then either interdict the
-- request, forwarding it to factored, or allow the request to pass
-- directly to the origin
--
function _do_remap()
  local cookies = parse_cookies(ts.client_request.header.Cookie)
  local cookie = cookies[factored_settings.cookie_name]

  local remote_addr = '0.0.0.0'
  if factored_settings.include_ip then
    ip, port, family = ts.client_request.client_addr.get_addr()
    remote_addr = ip
  end

  local rewrite = true

  ok, err = pcall(function()
    if cookie == nil then
      return false
    end
    return valid_auth_tkt(factored_settings, cookie.value, remote_addr)
  end)

  if ok then
    -- at this point, the return value is actually the value returned by the
    -- function
    if err then
      rewrite = false
    end
  else
    print('Error checking cookie: ' .. err)
  end

  -- this is where the request is interdicted, if the user is not
  -- determined to be authorized
  if rewrite then
    -- store clean values from the client url and then setup
    -- a hook to alter the headers sent to the upstream server
    pristine_host = ts.client_request.get_url_host()
    pristine_port = ts.client_request.get_url_port()
    pristine_scheme = ts.client_request.get_url_scheme()
    ts.hook(TS_LUA_HOOK_SEND_REQUEST_HDR, send_request)

    -- remap the upstream to point at the factored instance
    ts.client_request.set_url_host(factored_settings.host)
    ts.client_request.set_url_port(factored_settings.port)
    return TS_LUA_REMAP_DID_REMAP
  end

  return TS_LUA_REMAP_NO_REMAP
end

-- XXX: could make this configurable in the factored_settings maybe,
-- but it is a special case, only if there was an error with
-- the guts of the plugin
function factored_failed()
  local resp = 'HTTP/1.1 403 Forbidden\r\n' ..
               'Content-Type: text/plain\r\n\r\n' ..
               'Access Denied\n'
  ts.say(resp)
end

--
-- attempt to interdict the request, if necessary if there was an unhandled
-- error of some sort, prevent access to the upstream.
--
function do_remap()
  local status, ret = pcall(_do_remap)
  if status then
    return ret
  else
    ts.http.intercept(factored_failed) 
    return 0
  end
end
