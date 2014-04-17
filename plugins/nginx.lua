require 'package'
--ngx.log(ngx.ERR, package.path)

-- add plugin directory to load path
require 'debug'
local basepath = debug.getinfo(1).source
basepath = basepath:sub(2, string.len(basepath) - 7)  -- pull out actual path
package.path = package.path .. ';' .. basepath .. '?.lua'

require 'factored'

local function safe_tonumber(val)
  if type(val) == 'string' then
    return tonumber(val)
  else
    return val
  end
end


local settings = {
  secret=ngx.var.fsecret,
  cookie_name=ngx.var.fcookie_name,
  include_ip=safe_tonumber(ngx.var.finclude_ip),
  timeout=safe_tonumber(ngx.var.ftimeout),
}

if settings.include_ip == 0 then
  settings.include_ip = false
end

if settings.timeout == 0 then
  settings.timeout = false
end

local ip = '0.0.0.0'
if settings.include_ip == 1 then
  ip = ngx.var.remote_addr
end

if valid_auth_tkt(settings, ngx.var['cookie_' .. settings.cookie_name], ip) then
  return 1
else
  return 0
end
