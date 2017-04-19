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
--  Below is an example config file (note, "below" includes all content until
--  the end of the multi-line comment):

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

--]]


require 'string'
require 'math'
require 'package'
require 'os'

if string.find(package.path, factored_settings.basepath) == nil then
    ts.add_package_path(factored_settings.basepath .. '?.lua')
end
require 'factored'


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

  local intercept_with_factored = true

  ok, isvalid = pcall(function()
    if cookie == nil then
      -- no cookie at all means no valid auth_tkt :)
      return false
    end
    return valid_auth_tkt(factored_settings, cookie.value, remote_addr)
  end)

  if ok then
    -- if the pcall was successful, then the second value returned is
    -- the result of the method called
    -- thus, err would be true/false depending on whether or not the auth_tkt
    -- was determined to be valid.
    -- if the auth_tkt is valid, then there is no need to intercept with factored
    if isvalid then
      intercept_with_factored = false
    end
  else
    -- in this case, isvalid will be an error message captured by pcall
    ts.debug('Error checking cookie: ' .. isvalid)
    return 0
  end

  -- original upstream values
  local pristine_host = ts.client_request.get_url_host()
  local pristine_port = ts.client_request.get_url_port()
  local pristine_scheme = ts.client_request.get_url_scheme()

  -- this is where the request is interdicted, if the user is not
  -- determined to be authorized
  if intercept_with_factored then
    -- add headers to identify the original upstream to factored
    ts.server_request.header['X-Forwarded-Protocol'] = pristine_scheme
    final_host = pristine_host
    -- only add the port if it's non-standard. It would make ugly url's,
    -- and likely urls that are not expected otherwise
    if pristine_port ~= '80' and pristine_port ~= '443' then
        final_host = final_host .. ':' .. pristine_port
    end
    ts.server_request.header['Host'] = final_host

    -- remap the upstream to point at the factored instance
    ts.client_request.set_url_scheme(factored_settings.scheme)
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


return {
    factored_failed=factored_failed,
    do_remap=_do_remap
}
