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
from FanstiBgs.models.bgs_android import an_procedure_picture
from FanstiBgs.models.bgs_cloud import t_bgs_main_single_number, t_bgs_un

class CCommon:

    def upload_file(self):
        formdata = request.form
        files = request.files.get("file")
        an_procedure_picture_dict = {}
        import platform
        from FanstiBgs.config.secret import LinuxRoot, LinuxImgs, WindowsImgs, WindowsRoot
        if platform.system() == "Windows":
            rootdir = WindowsRoot + WindowsImgs
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