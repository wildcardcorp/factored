from pyramid.request import Request as BaseRequest
from factored.sm import getSessionManager
from pyramid.decorator import reify


class Request(BaseRequest):
    @reify
    def sm(self):
        return getSessionManager(self.environ)
