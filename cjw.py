import tornado.web
from util import con
from util import BaseHandler
from util import connect
import json
from util import map_class_time


class ViewClass(BaseHandler):
    l_names = [
        "课程编号",
        "课程名称",
        "教师姓名",
        "上课地点",
        "上课时间",
        "学院",
        "学分",
    ]

    @tornado.web.authenticated
    def get(self):
        # 检查用户权限
        role = self.get_secure_cookie("role")
        print(role)
        if role != b"student":
            # 这里先写着管理员，到时候改为不等于管理员，老师和学生可以查看自己选了哪门课
            # self.clear_cookie("role")
            self.redirect("/")
            return

        userid = self.get_secure_cookie("userid")
        userid = str(userid)[2:-1]
        print(userid)
        studentid = userid

        ##con = connect()
        cursor = con.cursor()
        mysqlsen = (
            "select course.number,course.name,teacher.name,academy.name,class.time,course.academyid,course.credit from course join class join teacher join academy join registration where registration.studentid='"
            + str(studentid)
            + "' and teacher.teacherid=class.teacherid and class.courseid=course.courseid and registration.classid=class.classid and course.academyid=academy.academyid"
        )
        cursor.execute(mysqlsen)
        print(cursor.statement)
        classes = list(cursor)
        cursor.close()
        # print(classes)
        for ind in range(len(classes)):
            classes[ind] = list(classes[ind])
            print(classes[ind][4])
            classes[ind][4] = map_class_time(classes[ind][4])
        print(classes)
        self.render(
            "view_class.html", classes=classes, l_names=self.l_names, role=role,
        )


class TplanShow(BaseHandler):  # 老师查看选课计划，为下一步选要教哪门课做准备
    l_names = ["课程计划名称", "开始时间", "结束时间", "年级", "学院"]

    @tornado.web.authenticated
    def get(self):
        # 检查用户权限
        role = self.get_secure_cookie("role")
        print(role)
        if role != b"teacher":
            # self.clear_cookie("role")
            self.redirect("/")  # 重定向，如果不是管理员，就跳转了
            return

        cursor = con.cursor()
        cursor.execute(
            "select plan.name,plan.start_time,plan.end_time,plan.grade,academy.name,plan.planid,plan.public from plan join academy where plan.academyid=academy.academyid"
        )
        plans = list(cursor)
        cursor.close()
        print(plans)
        self.render("plans.html", plans=plans, role=role, l_names=self.l_names)


class TselectCourse(BaseHandler):
    l_names = [
        "课程编号",
        "课程名称",
        "教学班编号",
        "学院",
        "上课地点",
        "上课时间",
        "学分",
    ]

    @tornado.web.authenticated
    def get(self):
        # 检查用户权限
        role = self.get_secure_cookie("role")
        print(role)
        if role != b"teacher":
            # self.clear_cookie("role")
            self.redirect("/")
            return
        cursor = con.cursor()

        sql = "select s from status where t = %s"
        cursor.execute(sql, ("course",))
        down = list(cursor)[0][0]
        print(down)

        planid = self.get_argument("planid")
        userid = self.get_secure_cookie("userid")
        userid = str(userid)[2:-1]

        teacherid = userid

        print(teacherid)

        mysqlsen = (
            "select course.number,course.name,class.classid,academy.name,class.place,class.time,course.credit,class.teacherid from course join class join plan join academy where plan.planid='"
            + planid
            + "' and plan.planid=class.planid and class.courseid=course.courseid and academy.academyid=course.academyid"
        )

        mysqlsen_t = "select class.time from class where class.teacherid='" + teacherid + "'"

        print(mysqlsen)
        cursor.execute(mysqlsen)
        classes = list(cursor)
        print(classes)

        print(mysqlsen_t)
        cursor.execute(mysqlsen_t)
        teacher_time_list = list(cursor)
        print(teacher_time_list)
        cursor.close()

        for ind in range(len(teacher_time_list)):
            teacher_time_list[ind] = teacher_time_list[ind][0]
            teacher_time_list[ind] = map_class_time(teacher_time_list[ind])
        print(teacher_time_list)

        # zjp添加，时间json字符串转成课表时间信息list
        for ind in range(len(classes)):
            classes[ind] = list(classes[ind])
            if classes[ind][7] is None:
                classes[ind][7] = -1

            print(classes[ind][5])

            classes[ind][5] = map_class_time(classes[ind][5])
        print(classes)
        cursor.close()
        self.render(
            "teacher_select_course.html",
            down=down,
            classes=classes,
            l_names=self.l_names,
            role=role,
            teacher_time_list=teacher_time_list,
            teacherid=teacherid,
            planid=planid,
        )

    def post(self):

        teacherid = self.get_argument("teacherid")
        classid = self.get_argument("classid")
        planid = self.get_argument("planid")
        # print("学生个数： "+studentnum)
        role = self.get_secure_cookie("role")
        print(role)
        if role != b"teacher":
            # self.clear_cookie("role")
            self.redirect("/")
            return

        cursor = con.cursor()
        mysqlsen = "update class set teacherid='" + teacherid + "' where classid='" + classid + "'"
        print(mysqlsen)
        cursor.execute(mysqlsen)
        con.commit()

        cursor.close()

        self.redirect("/tscourse?planid=" + planid)
