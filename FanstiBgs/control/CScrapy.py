# -*- coding: utf-8 -*-
import uuid, datetime, re, xlrd, requests
from html.parser import HTMLParser
from FanstiBgs.extensions.register_ext import db
from FanstiBgs.extensions.params_validates import parameter_required
from FanstiBgs.extensions.success_response import Success
from FanstiBgs.extensions.error_response import ParamsError, AuthorityError, ErrorGetNetwork
from FanstiBgs.models.bgs_scrapy import air_hwys_lines, air_hwys_dgr, air_hwys_dgr_container, air_hwys_dgr_level, \
    air_hwys_jd, t_bgs_un_dictionaries
from FanstiBgs.models.bgs_android import an_checklist
from flask import current_app

class MyHTMLParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.text = []

    def handle_data(self, data):
        self.text.append(data)


class MyHTMLParser2(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.text = []

    def handle_data(self, data):
        self.text.append(data)


class CScrapy():
    """
    def __init__(self):
        self.title = "=========={0}=========="
        from Fansti.services.Sscrapy import Sscrapy
        self.sscrapy = Sscrapy()
    """

    def get_cas(self):
        """
        获取cas
        """
        args = parameter_required(("token", "cas_name"))
        args["cas_name"] = str(args.get("cas_name")).upper()
        try:
            url = "http://www.ichemistry.cn/chemistry/{0}.htm".format(args["cas_name"])
            headers = {'Content-Type': 'application/xml'}
            req = requests.get(url)
            req.encoding = "utf-8"
            strResult = req.text
            parser = MyHTMLParser()
            parser.feed(strResult)
            length = len(parser.text)
            while length >= 0:
                parser.text[length - 1] = parser.text[length - 1].replace(" ", "").replace("\t", "").replace("\r","").replace("\n", "").replace("   ", "")
                if parser.text[length - 1].replace(" ", "") in ["\r\n", "\r\n\r\n", "\r\n\r\n\r\n", "]", "?", "\r\n\t",
                                                                "\r\n\t\t", "\r\n\t\t\t", "\r\n\t\t\t\t'", ":", ""]:
                    parser.text.remove(parser.text[length - 1])
                elif "\r\n" in parser.text[length - 1] or "var" in parser.text[length - 1]:
                    parser.text.remove(parser.text[length - 1])
                length = length - 1

            data = [
                {
                    "key": "基本信息",
                    "value": []
                },
                {
                    "key": "物理化学性质",
                    "value": []
                },
                {
                    "key": "安全信息",
                    "value": []
                },
                {
                    "key": "其他信息",
                    "value": []
                }
            ]
            keys = ["基本信息", "物理化学性质", "安全信息", "其他信息"]
            dict = []
            for row in parser.text:
                row_index = parser.text.index(row)
                dict.append(row)
                if "基本信息" in str(row):
                    current_app.logger.info(">>>>>>>>>>>make info:基本信息")
                    index = 0
                    item = {}
                    while True:
                        if ":" in parser.text[row_index + index + 1] or parser.text[row_index + index + 1] == "CAS登录号":
                            if parser.text[row_index + index + 1] != parser.text[row_index + 1]:
                                data[0]["value"].append(item)
                                item = {}

                            item["name"] = parser.text[row_index + index + 1]
                            item["value"] = []
                        else:
                            if parser.text[row_index + index + 1] in "物理化学性质":
                                break
                            else:
                                item["value"].append(parser.text[row_index + index + 1])
                        index += 1
                    current_app.logger.info(">>>>>>>>>>data:" + str(data))
                elif row in keys:
                    key_index = keys.index(row)
                    index = 0
                    item = {}
                    while True:
                        if ":" in parser.text[row_index + index + 1] or parser.text[row_index + index + 1] == "安全说明" \
                                or parser.text[row_index + index + 1] == "危险品标志" or parser.text[row_index + index + 1] == "危险类别码":
                            if parser.text[row_index + index + 1] != parser.text[row_index + 1]:
                                data[key_index]["value"].append(item)
                                item = {}

                            item["name"] = parser.text[row_index + index + 1]
                            item["value"] = []

                        else:
                            if parser.text[row_index + index + 1] in keys \
                                    or parser.text[row_index + index + 1] == "相关化学品信息":
                                break
                            else:
                                item["value"].append(parser.text[row_index + index + 1])
                        index += 1
            current_app.logger.info(dict)
            for row in dict:
                if "基本信息" in row:
                    current_app.logger.info(">>>>>>>>>>>>>>>>>>>>give me five>>>>>>>>>>>>>")
            while True:
                length = len(data[1]["value"])
                if data[1]["value"][length - 1]["name"] == "密度:":
                    break
                else:
                    data[1]["value"].remove(data[1]["value"][length - 1])
            return Success(data=data)
        except Exception as e:
            return ErrorGetNetwork()

    def get_flyno(self):
        args = parameter_required(("dest", "depa", "token"))

        args["depa"] = str(args.get("depa")).upper()
        args["dest"] = str(args.get("dest")).upper()

        all_airline = air_hwys_lines.query.filter(air_hwys_lines.depa == args["depa"],
                                                  air_hwys_lines.dest == args["dest"]).all()

        return Success(data=all_airline)

    def get_dgr(self):
        args = parameter_required(("token", "dgr_name"))
        args['dgr_name'] = str(args.get("dgr_name"))
        dgr = t_bgs_un_dictionaries.query.filter(t_bgs_un_dictionaries.UNNumberA == args["dgr_name"])\
            .first_("未找到")

        return Success(data=dgr)

    def add_checklist(self):

        return Success()

    def get_jd(self):
        """
        获取鉴定信息
        """
        args = parameter_required(("token", "jd_name"))

        jd_report = air_hwys_jd.query.filter(air_hwys_jd.chinesename.like("%{0}%".format(args.get("jd_name").upper()))).first()

        if not jd_report:
            return {
                "status": 405,
                "status_code": 405102,
                "message": "未查询到鉴定信息"
            }

        if not jd_report["appearance"]:
            if not jd_report["appearance2"]:
                appearance = "暂无信息"
            else:
                appearance = jd_report["appearance2"]
        else:
            if not jd_report["appearance2"]:
                appearance = jd_report["appearance"]
            else:
                appearance = jd_report["appearance"] \
                             + jd_report["appearance2"]
        if jd_report["endtime"]:
            endtime = str(jd_report["endtime"].year) + "/" + str(jd_report["endtime"].month) + "/" + str(
                jd_report["endtime"].day)
        else:
            endtime = "暂无出鉴定日期"
        data = [
            {
                "name": "中文品名",
                "value": jd_report["chinesename"]
            },
            {
                "name": "英文品名",
                "value": jd_report["englishname"]
            },
            {
                "name": "UN信息",
                "value": jd_report["unno"]
            },
            {
                "name": "颜色状态",
                "value": appearance
            },
            {
                "name": "委托公司",
                "value": jd_report["principal"]
            },
            {
                "name": "鉴定机构",
                "value": jd_report["identificationunits"]
            },
            {
                "name": "出鉴定日期",
                "value": endtime
            }
        ]
        return Success(data=data)

    def get_jd_names(self):
        args = parameter_required(("token", "jd_name"))
        jds = air_hwys_jd.query.filter(air_hwys_jd.chinesename.like("%{0}%".format(args.get("jd_name")))).all()
        jd_name_list = [jd.get("chinesename") for jd in jds]
        response = {}
        response['data'] = jd_name_list
        response["total"] = len(jd_name_list)
        return Success(data=response)