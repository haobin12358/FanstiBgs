# -*- coding: utf-8 -*-
from flask import Flask
from flask import Blueprint
from flask_cors import CORS


from .api.AHello import AHello
from .api.AUser import AUser
from .api.AShipping import AShipping
from .api.AProcedure import AProcedure
from .api.ACommon import ACommon
from .api.AMechandis import AMechandis
from .api.AScrapy import AScrapy

from .extensions.request_handler import error_handler, request_first_handler
from .config.secret import DefaltSettig
from .extensions.register_ext import register_ext
from FanstiBgs.extensions.base_jsonencoder import JSONEncoder
from FanstiBgs.extensions.base_request import Request


def register(app):
    bp = Blueprint(__name__, 'bp', url_prefix='/api')
    bp.add_url_rule('/hello/<string:hello>', view_func=AHello.as_view('hello'))
    bp.add_url_rule('/user/<string:user>', view_func=AUser.as_view("user"))
    bp.add_url_rule('/shipping/<string:shipping>', view_func=AShipping.as_view("shipping"))
    bp.add_url_rule('/procedure/<string:procedure>', view_func=AProcedure.as_view("procedure"))
    bp.add_url_rule('/common/<string:common>', view_func=ACommon.as_view("common"))
    bp.add_url_rule('/mechandis/<string:mechandis>', view_func=AMechandis.as_view("mechandis"))
    bp.add_url_rule('/scrapy/<string:scrapy>', view_func=AScrapy.as_view("scrapy"))
    app.register_blueprint(bp)


def after_request(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type'
    return resp


def create_app():
    app = Flask(__name__)
    app.json_encoder = JSONEncoder
    app.request_class = Request
    app.config.from_object(DefaltSettig)
    app.after_request(after_request)
    register(app)
    CORS(app, supports_credentials=True)
    request_first_handler(app)
    register_ext(app)
    error_handler(app)
    return app
