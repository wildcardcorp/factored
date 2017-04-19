require 'string'
require 'math'
require 'package'
require 'os'


-- XXX need to figure out a better way to load these from a plugin
--    XXX Maybe part of the configuration could be setting the LUA_PATH env variable
--        to include the settings.basepath value instead of having a settings.basepath?
-- sha256 = loadfile(settings.basepath .. 'sha.lua')()
-- loadfile(settings.basepath .. 'bit.lua')()
--sha256 = require 'sha'
--bit = require 'bit'
sha256 = loadfile(factored_settings.basepath .. 'sha.lua')()
loadfile(factored_settings.basepath .. 'bit.lua')()

function string:trim()
  return (self:gsub("^%s*(.-)%s*$", "%1"))
end


function string:split(sep)
  local sep, fields = sep or ":", {}
  local pattern = string.format("([^%s]+)", sep)
  self:gsub(pattern, function(c) fields[#fields+1] = c end)
  return fields
end

function url_decode(str)
  str = string.gsub (str, "+", " ")
  str = string.gsub (str, "%%(%x%x)",
      function(h) return string.char(tonumber(h,16)) end)
  str = string.gsub (str, "\r\n", "\n")
  return str
end

function parse_cookie(cookiestr)
  local key, val, flags = cookiestr:match("%s?([^=;]+)=?([^;]*)(.*)")
  if not key then
    return nil
  end

  local cookie = {key = key, value = val, flags = {}}
  for fkey, fval in flags:gmatch(";%s?([^=;]+)=?([^;]*)") do
    fkey = fkey:lower()
    cookie.flags[fkey] = fval
  end

  return cookie
end


function parse_cookies(cookies)
  if not cookies then
    return {}
  end
  local result = {}
  for k, cookiestr in pairs(cookies:split(';')) do
    local cookie = parse_cookie(cookiestr)
    if cookie ~= nil then
      result[cookie.key] = cookie
    end
  end
  return result
end


function is_equal(val1, val2)
  -- constant time comparison
  --
  local fails, dummy
  if string.len(val1) ~= string.len(val2) then
    return false
  end

  for i = 1,string.len(val1) do
    if (val1:sub(i,i) ~= val2:sub(i,i)) then
      fails = true
    else
      dummy = true  -- just here to make execution time the same
    end
  end
  return not fails
end


-- this function licensed under the MIT license (stolen from Paste)
function encode_ip_timestamp(ip, timestamp)
  local ip_chars = ''
  for k, v in pairs(ip:split('.')) do
    ip_chars = ip_chars .. string.char(tonumber(v))
  end
  local t = tonumber(timestamp)
  local ts_chars = string.char(bit.brshift(bit.band(t, 4278190080), 24)) ..
                   string.char(bit.brshift(bit.band(t, 16711680), 16)) ..
                   string.char(bit.brshift(bit.band(t, 65280), 8)) ..
                   string.char(bit.band(t, 255))
  return ip_chars .. ts_chars
end


function calculate_digest(settings, ip, timestamp, userid, tokens, user_data)
  timestamp = encode_ip_timestamp(ip, timestamp)
  local digest = sha256(timestamp .. settings.secret .. userid .. '\0' .. tokens .. '\0' .. user_data)
  return sha256(digest .. settings.secret)
end


function parse_ticket(settings, ticket, ip)
  -- Parse the ticket, returning a table of
  -- (timestamp, userid, tokens, user_data)
  ticket = ticket:trim()
  if ticket:sub(1, 1) == '"' then
    -- trim quotes around ticket value
    ticket = ticket:sub(2, string.len(ticket) - 1)
  end
  local digest_size = 32 * 2 -- only support for sha256 right now
  local digest = ticket:sub(1, digest_size)
  local timestamp = ticket:sub(digest_size + 1, digest_size + 8)
  timestamp = tonumber(timestamp, 16)
  if timestamp == nil then
    -- not a valid token
    return false
  end
  local user_chunk = ticket:sub(digest_size + 8 + 1, string.len(ticket))
  local user_data = user_chunk:split('!')
  local userid = user_data[1]
  local data = user_data[2]
  local tokens = ''
  if type(data) == 'string' then
    if string.find(data, '!') ~= nil then
      user_data = data:split('!', 1)
      tokens = user_data[1]
      user_data = user_data[2]
    else
      user_data = data
    end
  else
    user_data = ''
  end

  if userid ~= nil then
    userid = url_decode(userid)
  end

  local expected = calculate_digest(settings, ip, timestamp, userid, tokens, user_data)

  if not is_equal(expected, digest) then
    return false
  end

  tokens = tokens:split(',')

  local result = {}
  result['timestamp'] = timestamp
  result['userid'] = userid
  result['tokens'] = tokens
  result['user_data'] = user_data
  return result
end


function valid_auth_tkt(settings, cookie, ip)
  if cookie == nil then
    return false
  end

  local ticket = parse_ticket(settings, cookie, ip)
  if not ticket then
    return false
  end

  local now = os.time()

  if settings.timeout and settings.timeout ~= 0 then
    if ticket.timestamp + settings.timeout < now then
      -- the auth_tkt data has expired
      return false
    end
  end

  return true
end


function valid_auth_tkt_ret(settings, cookie, ip, ret)
  ret['val'] = valid_auth_tkt(setting, cookie, ip)
end
