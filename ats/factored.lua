-- Pull in the Traffic Server API.

require 'string'
require 'math'
require 'package'
require 'os'
require 'debug'

-- XXX need to figure out a better way to load these from a plugin
local basepath = '/home/nathan/code/factored/ats/'
sha256 = loadfile(basepath .. 'sha.lua')()
loadfile(basepath .. 'bit.lua')()

local TS = require 'ts'

function string:trim()
  return (self:gsub("^%s*(.-)%s*$", "%1"))
end


function string:split(sep)
  local sep, fields = sep or ":", {}
  local pattern = string.format("([^%s]+)", sep)
  self:gsub(pattern, function(c) fields[#fields+1] = c end)
  return fields
end


-- TODO
-- - auth request
-- - configure via ini
-- - configure multiple hosts

local scheme = 'http'
local host = '127.0.0.1'
local port = 8000
local secret = 'secret'
local cookie_name = 'pnutbtr'
local secure = false
local include_ip = false
local timeout = false
-- auth_tkt.hashalg = md5



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


function calculate_digest(ip, timestamp, userid, tokens, user_data)
  timestamp = encode_ip_timestamp(ip, timestamp)
  local digest = sha256(timestamp .. secret .. userid .. '\0' .. tokens .. '\0' .. user_data)
  return sha256(digest .. secret)
end


-- 74be7b3a9324f6723743e1cd8eed58d228048538f1f9ebbb46a993ac20484a7601d57409bab6c6c74182414430e757eebd641dbcd83bea42ddf56e45630dc38e534c5c22dmFuZ2hlZW1AZ21haWwuY29t!userid_type:b64unicode


function parse_ticket(ticket, ip)
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
  local user_chunk = ticket:sub(digest_size + 8 + 1, string.len(ticket))
  local user_data = user_chunk:split('!')
  local userid = user_data[1]
  local data = user_data[2]
  local tokens = ''
  if string.find(data, '!') ~= nil then
    user_data = data:split('!', 1)
    tokens = user_data[1]
    user_data = user_data[2]
  else
    user_data = data
  end

  local expected = calculate_digest(ip, timestamp, userid, tokens, user_data)

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


function valid_auth_tkt(request)
  local cookies = parse_cookies(request.headers.Cookie)
  local cookie = cookies[cookie_name]
  if cookie == nil then
    return false
  end

  local remote_addr = '0.0.0.0'
  if include_ip then
    ip, port, family = request.client_addr.get_addr()
    remote_addr = ip
  end

  local ticket = parse_ticket(cookie.value, remote_addr)
  if not ticket then
    return false
  end

  local now = os.time()

  if timeout then
    if ticket.timestamp + timeout < now then
      -- the auth_tkt data has expired
      return false
    end
  end

  return true
end


-- Compulsory remap hook. We are given a request object that we can modify if necessary.
function remap(request)
  -- Get a copy of the current URL.
  url = request:url()

  if not valid_auth_tkt(request) then
    url.host = host
    url.port = port
    -- Rewrite the request URL. The remap plugin chain continues and other plugins
    request:rewrite(url)
  end

end

-- Optional module initialization hook.
function init()
  return true
end
