"""
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from Fansti.flaskr import fansti
#http_server = HTTPServer(WSGIContainer(fansti))
#http_server.listen(443)
#IOLoop.instance().start()

server = HTTPServer(WSGIContainer(fansti), ssl_options={
           "certfile": "E:\\nginx-1.15.2\\conf\\cert\\",
           "keyfile": "E:\\nginx-1.15.2\\conf\\cert\\1533903359827.key"
    })
server.listen(443)
IOLoop.instance().start()
"""
from Fansti.flaskr import fansti as app

import sys 
from tornado.wsgi import WSGIContainer 
from tornado.httpserver import HTTPServer 
from tornado.ioloop import IOLoop 
# from run import app 
if len(sys.argv) == 2: 
	port = sys.argv[1] 
else: 
    port = 8001

http_server = HTTPServer(WSGIContainer(app)) 
http_server.listen(port) 
IOLoop.instance().start()