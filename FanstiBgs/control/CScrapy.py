# *- coding:utf8 *-
import sys
import os
sys.path.append(os.path.dirname(os.getcwd()))
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'
import uuid, datetime, re, xlrd, requests
from html.parser import HTMLParser
from FanstiBgs.extensions.params_validates import parameter_required
from FanstiBgs.extensions.success_response import Success
from FanstiBgs.extensions.error_response import ParamsError, AuthorityError, ErrorGetNetwork
from FanstiBgs.models.bgs_scrapy import air_hwys_lines, air_hwys_dgr, air_hwys_dgr_container, air_hwys_dgr_level

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
            for row in parser.text:
                row_index = parser.text.index(row)
                if "基本信息" in row:
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
            # print(data)
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
        args['dgr_name'] = str(args.get("dgr_name")).upper()
        dgr = air_hwys_dgr.query.filter(air_hwys_dgr.unno == args["dgr_name"]).all()
        dgr_list = []
        for raw in dgr:
            dgr_type = air_hwys_dgr_level.query.filter(air_hwys_dgr_level.dgr_id == raw["id"]).all()
            for row in dgr_type:
                dgr_con = air_hwys_dgr_container.query.filter(air_hwys_dgr_container.dgr_level_id == row["id"]).all()
                row["dgr_con"] = dgr_con
            raw["dgr_type"] = dgr_type
            dgr_list.append(raw)

        return Success(data=dgr_list)
