import tornado.web
from util import BaseHandler
from util import con
from util import map_class_time


class ViewPlan(BaseHandler):  # 主任查看选课计划
    l_names = ["课程计划名称", "开始时间", "结束时间", "年级", "学院", "发布", "编辑", "结束选课", "删除选课计划"]

    @tornado.web.authenticated
    def get(self):
        # 检查用户权限
        role = self.get_secure_cookie("role")
        print(role)
        if role != b"admin":
            self.render(
                "error.html", title="您没有权限访问此页面", message="只有教务主任可以查看所有选课计划"
            )  # 重定向，如果不是管理员，就跳转了
            return

        cursor = con.cursor()
        cursor.execute(
            "select plan.name, start_time, end_time, grade, academy.name, planid, public from plan join academy where plan.academyid = academy.academyid order by start_time asc"
        )
        plans = list(cursor)
        print(plans)
        self.render("plans.html", plans=plans, role=role, l_names=self.l_names)


class ViewTeachClass(BaseHandler):
    l_names = [
        "课程编号",
        "课程名称",
        "学院",
        "上课地点",
        "上课时间",
        "学分",
    ]

    @tornado.web.authenticated
    def get(self):
        # Enter检查用户权限
        role = self.get_secure_cookie("role")
        print(role)
        if role != b"teacher":
            # self.clear_cookie("role")
            self.redirect("/")
            return

        userid = self.get_secure_cookie("userid")
        userid = str(userid)[2:-1]
        print(userid)
        teacherid = userid

        cursor = con.cursor()
        mysqlsen = (
            "select course.number,course.name,academy.name,class.place,class.time,course.credit,class.classid,plan.public from course join class join teacher join academy join plan where class.teacherid='"
            + teacherid
            + "' and teacher.teacherid=class.teacherid and class.courseid=course.courseid and academy.academyid=course.academyid and plan.planid=class.planid"
        )

        print(mysqlsen)
        cursor.execute(mysqlsen)
        classes = list(cursor)
        print(classes)
        cursor.close()

        # zjp添加，时间json字符串转成课表时间信息list
        for ind in range(len(classes)):
            classes[ind] = list(classes[ind])
            print(classes[ind][4])
            classes[ind][4] = map_class_time(classes[ind][4])
        print(classes)

        self.render(
            "check_out_teach_classes.html", classes=classes, l_names=self.l_names, role=role,
        )

    def post(self):

        classid = self.get_argument("classid")

        # print("学生个数： "+studentnum)
        role = self.get_secure_cookie("role")
        print(role)
        if role != b"teacher":
            # self.clear_cookie("role")
            self.redirect("/")
            return

        cursor = con.cursor()
        mysqlsen = "update class set teacherid=null where classid='" + classid + "'"
        print(mysqlsen)
        cursor.execute(mysqlsen)
        con.commit()

        cursor.close()

        self.redirect("/teacher_class")


class EnterGrade(BaseHandler):
    l_names = ["姓名", "学号", "学院", "班级", "成绩"]

    @tornado.web.authenticated
    def get(self):
        # 检查用户权限
        role = self.get_secure_cookie("role")
        print(role)
        if role != b"teacher":
            # self.clear_cookie("role")
            self.redirect("/")
            return

        classid = self.get_argument("classid")
        print(classid)
        print("进入了登记成绩页面")

        cursor = con.cursor()
        mysqlsen = (
            "select student.name,student.number,academy.name,student.class,registration.grade,registration.registrationid from registration join student join academy where registration.classid='"
            + classid
            + "' and registration.studentid=student.studentid and student.academyid=academy.academyid"
        )
        print(mysqlsen)
        cursor.execute(mysqlsen)
        students = list(cursor)
        for ind in range(len(students)):
            students[ind] = list(students[ind])
        cursor.close()

        # BUG: 这个地方tuple不能修改有错误
        for ind in range(len(students)):
            if students[ind][4] is None:
                students[ind][4] = ""

        self.render(
            "enter_grade.html", students=students, classid=classid, role=role, l_names=self.l_names,
        )

    def post(self):
        scores = []
        classid = self.get_argument("classid")
        studentnum = self.get_argument("studentnum")
        # print("学生个数： "+studentnum)

        for i in range(int(studentnum)):
            score = self.get_argument("score" + str(i))
            registrationid = self.get_argument("registrationid" + str(i))
            print("registrationid=" + str(registrationid))
            if score is not "":
                score = int(score)
            else:
                score = -1
            scores.append(score)
            print("第" + str(i) + "个:  " + str(scores[i]))
            if score >= 0 and score <= 100:

                cursor = con.cursor()
                mysqlsen = (
                    "update registration set grade='"
                    + str(score)
                    + "' where registrationid='"
                    + registrationid
                    + "'"
                )
                print(mysqlsen)
                cursor.execute(mysqlsen)
                con.commit()
                print(("第" + str(i) + "个Yes!"))
                cursor.close()
        print(scores)
        print("提交")
        self.redirect("\enter_grade?classid=" + classid)


class ViewTeachStudent(BaseHandler):
    l_names = ["姓名", "学号", "性别", "生日", "学院", "班级", "入学年份", "联系方式", "通讯地址", "成绩"]

    @tornado.web.authenticated
    def get(self):
        # 检查用户权限
        role = self.get_secure_cookie("role")
        print(role)
        if role != b"teacher":
            # self.clear_cookie("role")
            self.redirect("/")
            return

        classid = self.get_argument("classid")
        # print(classid)
        print("进入了查看学生信息页面")

        cursor = con.cursor()
        mysqlsen = (
            "select student.name,student.number,student.ismale,student.birth,academy.name,student.class,student.enroll_year,student.contact,student.address,registration.grade from registration join student join academy where registration.classid='"
            + classid
            + "' and registration.studentid=student.studentid and student.academyid=academy.academyid"
        )
        print(mysqlsen)
        cursor.execute(mysqlsen)
        students = list(cursor)
        cursor.close()

        self.render(
            "teacher_student.html",
            students=students,
            l_names=self.l_names,
            classid=classid,
            role=role,
        )


if __name__ == "__main__":
    userid = b"123421321"
    userid = str(userid)[2:-1]
    print(userid)
