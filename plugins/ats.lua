--[[
--  These settings should match with your factored settings.
--]]
local settings = {
  -- this is factored host it's running on
  host='127.0.0.1',
  -- factored port it's running
  port=8000,
  -- do we also need to provide way to override factored auth path?
  -- auth tkt secret
  secret='secret',
  -- auth tkt cookie name
  cookie_name='pnutbtr',
  -- include ip for cookie value
  include_ip=false,
  -- manually handle cookie timeouts
  timeout=false,
  -- base path to the plugin source files
  basepath='/home/nathan/code/factored/ats/'
-- hashalg = md5
}

require 'string'
require 'math'
require 'package'
require 'os'

package.path = package.path .. ';/usr/local/factored/plugins/?.lua;' ..
  '/opt/factored/plugins?.lua;/home/nathan/code/factored/plugins/?.lua'

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

  if not valid_auth_tkt(settings, cookie, remote_addr) then
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
