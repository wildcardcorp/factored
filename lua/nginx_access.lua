local nginx_access = {}


--
-- validator: internal uri for validator upstream
-- authenticator: internal uri for authenticator upstream
--
function nginx_access.validate_auth(validator, authenticator)
    ngx.req.read_body()
    args = ngx.req.get_uri_args()
    uriargs = ngx.encode_args(args)
    foundsrc = false
    for key, value in pairs(args) do
        if key == "src" then
            foundsrc = true
        end
    end
    -- if the 'src' parameter is found, that means the validator and auth'r
    -- have a place to redirect traffic back too. otherwise, they need one
    if not foundsrc then
        fulluri = ngx.var.scheme.."://"..ngx.var.http_host..ngx.var.request_uri
        uriargs = "src=" .. ngx.escape_uri(fulluri) .. "&" .. uriargs
    end

    -- if the validator says the request has the appropriate param or cookie, or
    -- whatever, then the request should pass through to the upstream.
    local resp = ngx.location.capture(validator.."?"..uriargs)
    if resp.status == ngx.HTTP_OK then
        return
    end

    -- we redirect if the src param isn't found here because doing an exec
    -- is an interal request, and query params are kept by the nginx side in the
    -- request's uri, but the proxy_pass needs the uri args from the lua side's
    -- ngx.req.get_uri_args().
    --
    -- if a redirection is done to the same url, but with the src argument, then
    -- everything lines up and the user will get redirected back to the location
    -- in the src argument after a successful auth
    --
    if foundsrc then
        ngx.exec(authenticator.."?"..uriargs)
    else
        ngx.redirect(ngx.var.uri.."?"..uriargs, 302)
    end
end


return nginx_access
