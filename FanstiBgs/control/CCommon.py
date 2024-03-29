"""
公共api
create user: haobin12358
last update time: 2020-09-14
"""

import hashlib, datetime, requests, uuid, os
from flask import request, current_app

from FanstiBgs.extensions.params_validates import parameter_required
from FanstiBgs.extensions.error_response import ParamsError, AuthorityError, NoPreservationError
from FanstiBgs.extensions.request_handler import token_to_user_
from FanstiBgs.extensions.token_handler import usid_to_token
from FanstiBgs.extensions.register_ext import db
from FanstiBgs.extensions.success_response import Success
from FanstiBgs.models.bgs_android import an_procedure_picture, an_user
from FanstiBgs.models.bgs_cloud import t_bgs_main_single_number, t_bgs_un

class CCommon:

    def upload_file(self):
        formdata = request.form
        files = request.files.get("file")
        user_id = getattr(request, "user").id
        user = an_user.query.filter(an_user.user_id == user_id).first()
        an_procedure_picture_dict = {}
        an_procedure_picture_dict["user_id"] = user_id
        an_procedure_picture_dict["user_name"] = user.user_name
        an_procedure_picture_dict["createtime"] = datetime.datetime.now()
        import platform
        from FanstiBgs.config.secret import LinuxRoot, LinuxImgs, WindowsImgs, WindowsRoot, WindowsRoot_wxp
        if platform.system() == "Windows":
            # TODO 正式环境
            rootdir = WindowsRoot_wxp + "/photo"
        else:
            rootdir = LinuxRoot + LinuxImgs
        if not os.path.isdir(rootdir):
            os.mkdir(rootdir)
        if "FileType" not in formdata:
            return ParamsError("未找到FileType")
        filessuffix = str(files.filename).split(".")[-1]
        picture_id = str(uuid.uuid1())
        an_procedure_picture_dict["id"] = picture_id
        filename = formdata.get("FileType") + picture_id + "." + filessuffix
        an_procedure_picture_dict["type"] = formdata.get("FileType")
        an_procedure_picture_dict["file_name"] = filename
        filepath = os.path.join(rootdir, filename)
        an_procedure_picture_dict["file_src"] = filepath
        files.save(filepath)
        from FanstiBgs.config.http_config import API_HOST
        url = API_HOST + "/" + filename
        # TODO 同时存储到数据库中
        an_procedure_picture_dict["file_url"] = url
        with db.auto_commit():
            an_procedure_picture_instance = an_procedure_picture.create(an_procedure_picture_dict)
            db.session.add(an_procedure_picture_instance)
        return Success(data=url)