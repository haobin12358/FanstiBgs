"""
本文件用于处理用户的操作行为
create user: haobin12358
last update time: 2020-09-07
"""

import hashlib, datetime

from FanstiBgs.extensions.params_validates import parameter_required
from FanstiBgs.extensions.error_response import ParamsError, AuthorityError
from FanstiBgs.extensions.request_handler import token_to_user_
from FanstiBgs.extensions.token_handler import usid_to_token
from FanstiBgs.extensions.register_ext import db
from FanstiBgs.extensions.success_response import Success
from FanstiBgs.models.bgs_android import an_user

class CUser:

    def user_login(self):
        """用户登录"""
        data = parameter_required(("user_name", "user_password"))
        user = an_user.query.filter(an_user.isdelete == "0",
                                    an_user.user_name == data.get("user_name"))\
            .first_("未找到该账号或该账号被禁用")
        hash_password = hashlib.md5(data.get("user_password").encode("utf-8"))
        if user and hash_password.hexdigest() == user.user_password:
            token = usid_to_token(id=user.user_id, model="User", level=user.user_level, username=user.user_truename)
            user.fields = ["user_name", "user_level", "user_truename"]
            return Success("登录成功", data={"token": token, "user": user})
        else:
            return ParamsError("密码错误")

    def user_password_repeat(self):
        """用户修改密码"""
        data = parameter_required(("user_name", "user_password_old", "user_password_new", "user_password_repeat"))
        user = an_user.query.filter(an_user.isdelete == "0",
                                    an_user.user_name == data.get("user_name")) \
            .first_("未找到该账号或该账号被禁用")

        hash_password = hashlib.md5(data.get("user_password_old").encode("utf-8"))
        if data.get("user_password_new") != data.get("user_password_repeat"):
            return ParamsError("两次输入的新密码不同")

        if user and hash_password.hexdigest() == user.user_password:
            user_dict = {
                "user_password": hashlib.md5(data.get("user_password_new").encode("utf-8")).hexdigest(),
                "updatetime": datetime.datetime.now()
            }
            with db.auto_commit():
                user.update(user_dict, null="not")
            db.session.add(user)
            # user_instance = user_dict.update(user_id=user.user_id)
            return Success("修改成功请重新登录")
        else:
            return ParamsError("密码错误")
