# coding:utf-8
import os

import redis
import requests
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application
from tornado.options import define, options

import settings
import webhandlers


class MyApplication(Application):
    def __init__(self):
        handlers = [
            (r"/", webhandlers.IndexHandler),
            (r"/login", webhandlers.LoginHandler),
            (r"/search", webhandlers.SearchHandler),
            (r"/search_zp", webhandlers.SearchZhaopinHandler),
            (r"/resume/showresumedetail/", webhandlers.DetailHandler),
            (r"detail", webhandlers.DetailZhaopinHandler),
            (r"/vcode", webhandlers.ValidCodeHandler)
        ]
        config = dict(
            template_path=os.path.join(os.path.dirname(__file__), settings.TEMPLATE_ROOT),
            static_path=os.path.join(os.path.dirname(__file__), settings.STATIC_ROOT),
            #xsrf_cookies=True,
            cookie_secret="__TODO:_E720135A1F2957AFD8EC0E7B51275EA7__",
            autoescape=None,
            debug=settings.DEBUG
        )

        self.redis = redis.Redis(host=settings.REDIS_HOST,
                                 port=settings.REDIS_PORT,
                                 db=settings.REDIS_DB)

        self.authed_user = {}
        self.sessions = {'liepin': requests.Session(),
                         'zhaopin': requests.Session()}
        Application.__init__(self, handlers, **config)


def run():
    define("host", default=settings.HOST, help="run on the given host")
    define("port", default=settings.PORT, help="run on the given port", type=int)
    options.parse_command_line()

    http_server = HTTPServer(MyApplication())
    http_server.listen(port=options.port, address=options.host)

    IOLoop.instance().start()


if __name__ == '__main__':
    run()
