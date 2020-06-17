# coding=utf-8
import tornado.web
import os
from tornado.options import define, options
from tornado.escape import json_encode
import base64
import uuid


from util import connect, BaseHandler
from hl import Login, Logout, Index, EditPlan, ChooseClass, Finance, ChangePasswd, UserInfo
from zjp import EditStudent, EditTeacher, StudentViewGrades, EndRegistration, EditCourse
from cjw import ViewClass, TplanShow, TselectCourse
from wyyy import ViewPlan, ViewTeachClass, EnterGrade, ViewTeachStudent


define("port", default=8000, help="run on the given port", type=int)


if __name__ == "__main__":
    tornado.options.parse_command_line()
    randstring = base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)  # 每次运行生成新的加密字符串
    app = tornado.web.Application(
        handlers=[
            (r"/", Index),  # 主页
            (r"/login", Login),  # 登录
            (r"/login/(\w+)", Login),  # 登录
            (r"/logout", Logout),  # 登出
            (r"/editstudent", EditStudent),
            (r"/editstudent/(\w+)", EditStudent),
            (r"/editteacher", EditTeacher),
            (r"/editteacher/(\w+)", EditTeacher),
            (r"/studentviewgrades", StudentViewGrades),  # 学生查看成绩
            (r"/userinfo", UserInfo),  # 展示用户信息
            (r"/courses", ViewClass),  # 学生选课/老师选教的课
            (r"/changepasswd", ChangePasswd),  # 修改密码
            (r"/teacher_class", ViewTeachClass),  # 老师查看课程信息(wy加的)
            (r"/teacher_student", ViewTeachStudent),  # 老师查看选课学生(wy加的)
            (r"/enter_grade", EnterGrade),  # 老师上成绩
            (r"/plans", ViewPlan),  # 主任查看所有选课计划
            (r"/tplans", TplanShow),  # 教师查看选课计划 cjw  加
            (r"/tscourse", TselectCourse),  # 教师选教哪些课 全称 teacher_select_course cjw加
            (r"/editPlan", EditPlan),
            (r"/editPlan/(\w+)", EditPlan),
            (r"/chooseClass", ChooseClass),
            (r"/chooseClass/(\w+)", ChooseClass),
            # (r"/edit_plan", EditPlan),  # 编辑选课计划
            (r"/endregistration", EndRegistration),  # 结束选课计划
            # (r"/edit_user", EditUser),  # 编辑用户信息
            (r"/finance/(\w+)", Finance),
            (r"/editCourse", EditCourse),
            (r"/editCourse/(\w+)", EditCourse),
        ],
        template_path=os.path.join(os.path.dirname(__file__), "templates",),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        cookie_secret=randstring,
        # xsrf_cookies=True,
        login_url="/login",  # 未登录用户默认重定向到这
    )
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
(r"/finance/(\w+)", Finance),
