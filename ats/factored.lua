-- Pull in the Traffic Server API.
local TS = require 'ts'

require 'string'
require 'math'

local basepath = '/home/nathan/code/factored/ats/'
loadfile(basepath .. 'sha.lua')

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
  ip_chars = ''
  for k, v in pairs(ip:split('.')) do
    ip_chars = ip_chars .. string.char(tonumber(v))
  end
  t = tonumber(timestamp)
  ts_chars = string.char(bit32.rshift(bit32.band(t, 4278190080), 24)) ..
             string.char(bit32.rshift(bit32.band(t, 16711680), 16)) ..
             string.char(bit32.rshift(bit32.band(t, 65280), 8)) ..
             string.char(bit32.band(t, 255))

  return ip_chars .. ts_chars
end


function calculate_digest(ip, timestamp, userid, tokens, user_data)
  digest = sha256(encode_ip_timestamp(ip, timestamp) .. secret .. userid .. '\0' .. tokens .. '\0' .. user_data)
  return sha256(digest .. secret)
end


-- 74be7b3a9324f6723743e1cd8eed58d228048538f1f9ebbb46a993ac20484a7601d57409bab6c6c74182414430e757eebd641dbcd83bea42ddf56e45630dc38e534c5c22dmFuZ2hlZW1AZ21haWwuY29t!userid_type:b64unicode


function parse_ticket(ticket, ip)
  -- Parse the ticket, returning a table of
  -- (timestamp, userid, tokens, user_data).
  ticket = ticket.trim()
  digest_size = 32 * 2
  digest = ticket.sub(0, digest_size)
  timestamp = tonumber(ticket.sub(digest_size + 1, digest_size + 8 + 1), 16)
  userid, data = ticket.sub(digest_size + 8 + 1, string.len(ticket)):split('!')[2]
  if string.find(data, '!') ~= nil then
    tokens, user_data = data.split('!', 1)
  else
    tokens = ''
    user_data = data
  end

  expected = calculate_digest(ip, timestamp, userid, tokens, user_data)

  if not is_equal(expected, digest) then
    return false
  end

  tokens = tokens:split(',')

  result = {}
  result['timestamp'] = timestamp
  result['userid'] = userid
  result['tokens'] = tokens
  result['user_data'] = user_data
  return result
end


function valid_auth_tkt(request)
  cookies = parse_cookies(request.headers.Cookie)
  cookie = cookies[cookie_name]
  if cookie == nil then
    return false
  end

  remote_addr = '0.0.0.0'
  if include_ip then
    ip, port, family = request.client_addr.get_addr()
    remote_addr = ip
  end

  ticket = parse_ticket(cookie, ip)
  if not ticket then
    return false
  end

  now = os.time()
  if timeout then
    if ticket.timestamp + self.timeout < now then
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

  print(string.format('remapping %s://%s', url.scheme, url.host))
  if not valid_auth_tkt(request) then
    url.host = host
    url.port = port
    -- Rewrite the request URL. The remap plugin chain continues and other plugins
    request:rewrite(url)
  end

end

-- Optional module initialization hook.
function init()
  print(string.format('init called by Traffic Server %s', TS.VERSION))
  return true
end
