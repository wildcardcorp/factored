--[[
--  These settings should match with your factored settings.
--]]
local settings = {
  -- this is factored host it's running on
  host='127.0.0.1',
  -- factored port it's running
  port=8000,
  -- do we also need to provide way to override factored auth path?
  -- auth tkt cookie name
  cookie_name='pnutbtr',
  -- auth tkt secret
  secret='secret',
  -- include ip for cookie value
  include_ip=false,
  -- manually handle cookie timeouts
  timeout=false,
  -- base path to the plugin source files
  basepath='/home/nathan/code/factored/ats/'
-- hashalg = md5
}

local ts = require 'ts'

require 'string'
require 'math'
require 'package'
require 'os'

-- add plugin directory to load path
require 'debug'
local basepath = debug.getinfo(1).source
basepath = basepath:sub(2, string.len(basepath) - 7)  -- pull out actual path
package.path = package.path .. ';' .. basepath .. '?.lua'

require 'factored'

-- Compulsory remap hook. We are given a request object that we can modify if necessary.
function remap(request)
  -- Get a copy of the current URL.
  url = request:url()
  local cookies = parse_cookies(request.headers.Cookie)
  local cookie = cookies[settings.cookie_name]

  local remote_addr = '0.0.0.0'
  if settings.include_ip then
    ip, port, family = request.client_addr.get_addr()
    remote_addr = ip
  end

  local rewrite = true

  ok, err = pcall(function()
    if cookie == nil then
      return false
    end
    return valid_auth_tkt(settings, cookie.value, remote_addr)
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

  if rewrite then
    url.host = settings.host
    url.port = settings.port
    -- Rewrite the request URL. The remap plugin chain continues and other plugins
    request:rewrite(url)
  end

end

-- Optional module initialization hook.
function init()
  return true
end
