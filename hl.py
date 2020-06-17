from util import BaseHandler, connect, get_md5
import tornado.web
import json
import time
import util
import mysql
from util import dump_err
from decimal import *
import time
import tornado.httpclient
import urllib
from captcha.image import ImageCaptcha
import random
import os


class Login(BaseHandler):
    def get(self):
        print("login")

        self.render(
            "login.html", next=self.get_argument("next", "/"), disable_nav=True,
        )

    def post(self, action=None):
        if action == "get_captcha":
            image = ImageCaptcha()
            data = image.generate("1234")
            captcha = random.randint(1000, 9999)
            ts = time.time()
            image.write(
                str(captcha),
                os.path.join(os.path.dirname(__file__), "static/captcha/{}.png".format(ts)),
            )
            self.write(
                json.dumps(
                    {
                        "status": "success",
                        "src": util.base_url + "/static/captcha/{}.png".format(ts),
                        "value": captcha,
                    }
                )
            )
            return

        username = self.get_argument("username")
        passwd = self.get_argument("passwd")
        next = self.get_argument("next")
        print(next)

        cursor = util.con.cursor()
        query = "select passwd, user_type, userid from passwd where username = %s"
        cursor.execute(query, (username,))
        info = list(cursor)
        print(cursor.lastrowid, cursor.statement)
        cursor.close()
        if len(info) != 1:
            print("user dont exist")
            self.write(
                json.dumps({"status": "fail", "message": "用户名不正确，请重新尝试"}, ensure_ascii=False)
            )
            return
        info = info[0]
        print(info)

        passwd = get_md5(passwd)
        print(info[0], passwd)
        if info[0] != passwd:
            print("passwd not match, relogin")
            self.write(
                json.dumps({"status": "fail", "message": "用户名或密码错误，请重新尝试"}, ensure_ascii=False)
            )
            return

        print("matched")
        if info[1] == 0:
            role = "admin"
        elif info[1] == 1:
            role = "teacher"
        elif info[1] == 2:
            role = "student"
        else:
            self.write_error(666, "role {} is not a valid role".format(info[1]))
        print("login info ", info)
        self.set_secure_cookie("userid", str(info[2]))
        self.set_secure_cookie("role", role)

        if next == "/login":
            next = "/"
        self.write(json.dumps({"status": "success", "next": next}, ensure_ascii=False))


class Logout(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.clear_cookie("role")
        self.redirect("/login")


class ChangePasswd(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        role = self.get_secure_cookie("role")
        if role not in [b"admin", b"student", b"teacher"]:
            self.render("error.html", title="您无权查看本页面", message="请先登录")
            return
        self.render("changepswd.html", role=role)

    @tornado.web.authenticated
    def post(self):
        role = self.get_secure_cookie("role")
        userid = self.get_secure_cookie("userid")
        print("ols pswd", self.get_argument("old_pswd"))
        input_old_pswd = get_md5(self.get_argument("old_pswd"))
        input_new_pswd = get_md5(self.get_argument("new_pswd"))
        print(userid)
        cursor = util.con.cursor()
        if role == b"student":
            user_type = 2
        elif role == b"teacher":
            user_type = 1
        elif role == b"admin":
            user_type = 0
        cursor.execute(
            "select passwd from passwd where userid = %s and user_type = %s", (userid, user_type)
        )
        print(cursor.statement)
        select_old_pswd = list(cursor)[0][0]
        print(select_old_pswd, input_old_pswd)

        if input_old_pswd != select_old_pswd:
            self.write(
                json.dumps({"result": "fail", "reason": "输入的旧密码错误，请重新输入"}, ensure_ascii=False)
            )
            return

        mysql = "update passwd set passwd= %s where userid = %s"
        cursor.execute(mysql, (input_new_pswd, userid))
        util.con.commit()
        cursor.close()
        self.write(json.dumps({"result": "success"}))


class Index(BaseHandler):
    @tornado.web.authenticated  # 只有 current_user (上面那个get_current_user的返回值)不为空，才会执行方法
    def get(self):
        self.render("index.html", role=self.get_secure_cookie("role"))


class UserInfo(BaseHandler):
    S_info = [
        "姓名",
        "学号",
        "性别",
        "出生日期",
        "学院",
        "班级",
        "入学年份",
        "联系方式",
        "家庭住址",
        "账户余额",
        "冻结金额",
    ]
    T_info = [
        "姓名",
        "学号",
        "性别",
        "出生日期",
        "联系方式",
        "家庭地址",
        "学院",
        "职称",
        "薪资",
        "入职时间",
    ]

    @tornado.web.authenticated
    def get(self):
        print(len(self.S_info), len(self.T_info))
        role = self.get_secure_cookie("role")
        userid = self.get_secure_cookie("userid")
        print(role)
        userid = str(userid)[2:-1]
        print(userid)
        if role != b"admin" and role != b"student" and role != b"teacher":
            self.render("error.html", title="您无权查看本页面", message="请使用正确的账户登录")
            return

        cursor = util.con.cursor()
        if role == b"admin" or role == b"teacher":
            cursor.execute("select * from teacher where teacherid=%s", (userid,))
            info = list(list(cursor)[0])
            print(info)
            del info[0]
            if info[2] == 1:
                info[2] = "男"
            else:
                info[2] = "女"
            sql = "select name from academy where academyid = %s"
            cursor.execute(sql, (info[6],))
            info[6] = list(cursor)[0][0]
            cursor.close()
            self.render("userinfo.html", INFO=self.T_info, info=info, role=role)
            return

        if role == b"student":
            cursor.execute("select * from student where studentid=%s", (userid,))
            info = list(list(cursor)[0])
            del info[-1]

            print(info)
            if info[2] == 1:
                info[2] = "男"
            else:
                info[2] = "女"
            # 替学院
            sql = "select name from academy where academyid = %s"
            cursor.execute(sql, (info[5],))
            print(cursor.statement)
            academy = list(cursor)
            info[6] = academy[0][0]

            # 补全余额和冻结
            sql = "select balance, frozen from finance where studentid = %s"
            cursor.execute(sql, (info[0],))
            finan = list(cursor)[0]
            print(finan)
            info.append(finan[0])
            info.append(finan[1])
            del info[0]

            cursor.close()
            self.render("userinfo.html", INFO=self.S_info, info=info, role=role)
            return


class EditPlan(BaseHandler):
    """编辑选课计划内容."""

    @tornado.web.authenticated
    def get(self):
        # 检查用户权限
        role = self.get_secure_cookie("role")
        print(role)
        if role != b"admin":
            self.render("error.html", title="您没有权限访问此页面", message="只有教务主任可以修改选课计划")
            return

        grade_names = [
            "大一上",
            "大一下",
            "大二上",
            "大二下",
            "大三上",
            "大三下",
            "大四上",
            "大四下",
            "研一上",
            "研一下",
            "研二上",
            "研二下",
        ]
        grade_vals = [x for x in range(1, 13)]
        planid = self.get_argument("planid", None)
        print("current planid is ", planid)
        cursor = util.con.cursor()
        query = "select * from course"
        cursor.execute(query)
        courses = list(cursor)

        query = "select * from academy"
        cursor.execute(query)
        academies = list(cursor)

        cursor.close()
        print("all the courses and academies are", courses, academies)
        planinfo = ["" for x in range(10)]
        planinfo[5] = [["", ""] for x in range(4)]
        planinfo[6] = [["", ""] for x in range(4)]

        print("fake plan info", planinfo)
        if planid == None:
            self.render(
                "editPlan.html",
                curr_day=time.strftime("%Y-%m-%d", time.localtime()),
                role=self.get_secure_cookie("role"),
                type="添加",
                grade_vals=grade_vals,
                grade_names=grade_names,
                courses=courses,
                planid=planid,
                academies=academies,
                planinfo=planinfo,
                classes="",
                class_list="",
            )
        else:
            # 这里需要把选课的数据放上去
            cursor = util.con.cursor()
            sql = "select * from class where planid = %s"
            cursor.execute(sql, (planid,))
            classes = list(cursor)

            sql = "select * from plan where planid = %s"
            cursor.execute(sql, (planid,))
            planinfo = list(list(cursor)[0])

            cursor.close()

            # planinfo = list(planinfo[0])
            planinfo[5] = planinfo[5].isoformat().split("T")
            planinfo[6] = planinfo[6].isoformat().split("T")

            print("planinfo", planinfo)

            class_list = ""
            for ind in range(len(classes)):
                classes[ind] = list(classes[ind])
                classes[ind][5] = json.loads(classes[ind][5])
                class_list += str(classes[ind][0]) + ","  # 最后必须有一个 ,
            print("classes info", classes)

            self.render(
                "editPlan.html",
                curr_day=time.strftime("%Y-%m-%d", time.localtime()),
                role=self.get_secure_cookie("role"),
                type="修改",
                grade_vals=grade_vals,
                grade_names=grade_names,
                courses=courses,
                planid=planid,
                academies=academies,
                classes=classes,
                class_list=class_list,
                planinfo=planinfo,
            )

    @tornado.web.authenticated
    def post(self, action):
        """删除选课计划"""
        if action == "delete":
            planid = self.get_argument("planid")

            # 1. 如果不存在，不能删除
            sql = "select public from plan where planid = %s"
            cursor = util.con.cursor()
            cursor.execute(sql, (planid,))
            print(cursor.statement)
            ispublic = list(cursor)
            print("ispublic", ispublic)
            if len(ispublic) == 0:
                dump_err(self, "不能删除不存在的选课计划")
                cursor.close()
                return

            # 2. 如果已公开，不能删除
            ispublic = ispublic[0][0]
            if ispublic == 1:
                dump_err(self, "不能删除已公开的选课计划")
                cursor.close()
                return

            # 3. 删除教学班
            sql = "delete from class where planid = %s"
            cursor.execute(sql, (planid,))
            util.con.commit()

            # 4. 删除计划记录
            sql = "delete from plan where planid = %s"
            cursor.execute(sql, (planid,))
            print("delete plan: ", cursor.statement)
            util.con.commit()
            cursor.close()

            self.write(json.dumps({"status": "success", "message": "选课计划和计划中的教学班删除成功"}))

        """公开选课计划"""
        if action == "publish":
            planid = self.get_argument("planid")
            cursor = util.con.cursor()
            # 1. 删除没老师的课程
            sql = "select classid from class where planid = %s and teacherid is null "
            cursor.execute(sql, (planid,))
            classes_without_teacher = list(cursor)
            classes_without_teacher = [x[0] for x in classes_without_teacher]
            print("没老师的课", classes_without_teacher)
            if len(classes_without_teacher) != 0:
                sql = "delete from class where classid in (" + "%s, " * len(classes_without_teacher)
                sql = sql[:-2]
                sql = sql + ")"
                cursor.execute(sql, classes_without_teacher)
                print(cursor.statement)

            # 2. 选课计划设置为公开
            sql = "update plan set public = 1 where planid = %s"
            cursor.execute(sql, (planid,))

            cursor.close()
            util.con.commit()
            msg = "选课计划公开成功"
            if len(classes_without_teacher) != 0:
                msg += "，删除了{}".format(classes_without_teacher)
            self.write(json.dumps({"status": "success", "message": msg,}, ensure_ascii=False,))
            return

        """编辑选课计划"""
        if action == "save":
            planid = self.get_argument("planid")
            curr_time = util.curr_time()
            start_daytime = (
                self.get_argument("start_day") + " " + self.get_argument("start_time") + ":00"
            )
            if start_daytime <= curr_time:
                dump_err(self, "选课计划开始时间需要晚于当前时间")
                return
            if planid == "None":
                planid = self.insert_plan()
            else:
                self.update_plan(planid)

            # PLAN: 这里判断如果有选课计划（是修改），那么当前选课计划必须还没有发布
            self.insert_class(planid)
            self.update_class(planid)
            self.del_class(planid)
            self.write(
                json.dumps(
                    {"status": "success", "message": "成功添加选课计划", "planid": planid},
                    ensure_ascii=False,
                )
            )

    def update_plan(self, planid):
        cursor = util.con.cursor()
        sql = "UPDATE `plan` SET `name` = %s, `start_time` = %s, `end_time` = %s, `grade` = %s, `academyid` = %s WHERE `planid` = %s"
        vals = [
            "name",
            "start_day",
            "start_time",
            "end_day",
            "end_time",
            "grade",
            "academyid",
        ]
        vals = [self.get_argument(n) for n in vals]
        vals[1] = vals[1] + " " + vals[2]
        vals[3] = vals[3] + " " + vals[4]
        del vals[4]  # 注意顺序不可以修改
        del vals[2]
        vals.append(planid)
        print("updata", vals)
        cursor.execute(sql, vals)
        util.con.commit()

    def del_class(self, planid):
        del_class_list = util.purge_list(self.get_argument("del_class_list").split(","))

        for del_class in del_class_list:
            if "_" in del_class:
                continue
            cursor = util.con.cursor()
            sql = "delete from class where classid = %s"
            print(del_class)
            try:
                cursor.execute(sql, (int(del_class),))
            except mysql.connector.errors.DataError as e:
                self.write(json.dumps({"status": "fail", "message": e}))
                print(e)
                return
            else:
                util.con.commit()
                print("deleted class ", (del_class,))
            finally:
                cursor.close()

    def update_class(self, planid):
        """更新课程信息，所有的带 _ 的课程是新添加的，在insert_plan里处理，其余的都更新一遍

        Parameters
        ----------
        planid : type
            Description of parameter `planid`.

        Returns
        -------
        type
            Description of returned object.

        """
        class_list, class_time, class_place = self.get_classes()
        print("更新课程信息", class_list, class_time, class_place)
        for ind in range(len(class_list)):
            if "_" in class_list[ind]:
                continue
            cursor = util.con.cursor()
            print(class_list[ind], class_time[ind])
            sql = "UPDATE `class` SET `place` = %s, `time` =  %s WHERE `classid` =  %s"
            try:
                cursor.execute(sql, (class_place[ind], class_time[ind], int(class_list[ind])))
                print(cursor.statement)
            except mysql.connector.errors.DataError as e:
                self.write(json.dumps({"status": "fail", "message": e}))
                print(e)
                return
            else:
                util.con.commit()
            finally:
                cursor.close()

    def insert_plan(self):
        # 添加选课计划
        cursor = util.con.cursor()
        query = "INSERT INTO `plan`(`name`,`start_time`,`end_time`,`grade`,`academyid`)VALUES (%s, %s,%s,%s,%s)"
        vals = [
            "name",
            "start_day",
            "start_time",
            "end_day",
            "end_time",
            "grade",
            "academyid",
        ]
        vals = [self.get_argument(name) for name in vals]
        vals[1] = vals[1] + " " + vals[2]
        vals[3] = vals[3] + " " + vals[4]
        del vals[4]  # 注意顺序不可以修改
        del vals[2]
        print("添加选课参数", vals)
        try:
            cursor.execute(query, vals)
        except mysql.connector.errors.DataError as e:
            self.write(json.dumps({"status": "fail", "message": e}))
            print("错误信息", e)
            return
        else:
            res = list(cursor)
            planid = cursor.lastrowid
            print("新选课计划id", planid)
            util.con.commit()
        finally:
            cursor.close()
        return planid

    def insert_class(self, planid):
        # 添加教学班级
        class_list, class_time, class_place = self.get_classes()
        for ind in range(len(class_list)):
            if "_" in class_list[ind]:  # 如果有 _ 说明是新添加的课
                courseid = class_list[ind].split("_")[0]
                sql = "INSERT INTO `class` (`courseid`,`planid`,`place`,`time`) VALUES (%s, %s, %s, %s)"
                print("即将插入课程的信息", (courseid, planid, class_place[ind], class_time[ind]))
                cursor = util.con.cursor()
                try:
                    cursor.execute(sql, (courseid, planid, class_place[ind], class_time[ind]))
                except mysql.connector.errors.DataError as e:
                    self.write(json.dumps({"status": "fail", "message": e}))
                    print(e)
                    return
                else:
                    pass
                finally:
                    cursor.close()
                    util.con.commit()

    def get_classes(self):
        class_list = util.purge_list(self.get_argument("class_list").split(","))
        del_class_list = util.purge_list(self.get_argument("del_class_list").split(","))
        print("purges list", class_list, del_class_list)
        for del_class in del_class_list:
            class_list.remove(del_class)
        print("deleted class list", class_list)

        class_week = [self.get_argument("{}_week".format(clas)) for clas in class_list]
        class_time = [self.get_argument("{}_time".format(clas)) for clas in class_list]
        class_place = [self.get_argument("{}_place".format(clas)) for clas in class_list]

        assert len(class_week) == len(class_time), "{}\n\n{}长度不相等".format(class_week, class_time)
        class_time = [json.dumps([[int(x), int(y)]]) for x, y in zip(class_week, class_time)]
        print("教学班列表", class_list, class_time)
        return class_list, class_time, class_place


class ChooseClass(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        util.check_role(self, "student")
        sid = self.get_secure_cookie("userid")
        print("当前学生的id是", sid)

        cursor = util.con.cursor()
        sql = "select enroll_year, academyid from student where studentid = %s"
        cursor.execute(sql, (sid,))
        enroll_year, academyid = list(cursor)[0]
        grade = util.get_grade(enroll_year)
        print("学生的入学年，学期和学院分别是", enroll_year, grade, academyid)

        sql = "select * from plan where grade = %s and academyid = %s and public = '1'"
        cursor.execute(sql, (grade, academyid))
        plans = list(cursor)
        print("该学生能参加的选课计划有", plans)
        cursor.close()

        self.render(
            "chooseClass.html",
            title="选课页面",
            plans=plans,
            role=b"student",
            studentid=self.get_secure_cookie("userid"),
            curr_time=util.curr_time(),
        )

    @tornado.web.authenticated
    async def post(self, action):
        if action == "get_class":
            # 1. 获取所有的课程
            classes = self.get_classes()
            sid = self.get_argument("sid")
            print("所有的课程为", classes)

            # 2. 对class按照学生设定的顺序进行排序
            cursor = util.con.cursor()
            sql = "select clsids from student where studentid = %s "
            cursor.execute(sql, (sid,))
            clsids = list(cursor)[0][0]
            if clsids is not None:  # 如果是none是学生没设过排序
                # 检查排序的clsid和当前计划的clsid是否完全相同
                clsids = json.loads(clsids)
                curr_plan_clas = set([cls[0] for cls in classes])
                print(curr_plan_clas, clsids, set(clsids))
                if curr_plan_clas != set(clsids):
                    # 有出入，这个排序无效，清空
                    sql = "update student set clsids = null where studentid = %s"
                    cursor.execute(sql, (sid,))
                    util.con.commit()
                else:
                    # 合法，按照排序修改课程顺序
                    sorted_class = []
                    for clsid in clsids:
                        for clas in classes:
                            if clsid == clas[0]:
                                sorted_class.append(clas)
                                break
                    print("sorted_class", sorted_class)
                    classes = sorted_class

            # 3. 补全class中的老师，课程名称，是否选择信息
            for ind in range(len(classes)):
                classes[ind] = list(classes[ind])
                print("curr clas info", classes[ind])
                sql = "select name from course where courseid = %s"
                cursor.execute(sql, (classes[ind][1],))
                print(cursor.statement)
                course_name = list(cursor)[0][0]
                classes[ind].append(str(course_name))

                sql = "select name from teacher where teacherid = %s"
                cursor.execute(sql, (classes[ind][3],))
                print(cursor.statement)
                teacher_name = list(cursor)[0][0]
                classes[ind].append(teacher_name)
                classes[ind].append(util.map_class_time(classes[ind][5]))

                sql = "select is_1st from choice_temp where studentid = %s and classid = %s"
                cursor.execute(sql, (sid, classes[ind][0]))
                print("+_+_+", cursor.statement)
                is_1st = list(cursor)
                print("is_1st", is_1st)
                if len(is_1st) == 0:
                    classes[ind].append(-1)
                else:
                    classes[ind].append(is_1st[0][0])

                print("补全后课程信息", classes[ind])

            # 4. 获取选课计划信息
            sql = "select * from plan where planid = %s"
            cursor.execute(sql, (self.get_argument("planid"),))
            planinfo = list(list(cursor)[0])
            planinfo[5] = planinfo[5].isoformat().replace("T", " ")
            planinfo[6] = planinfo[6].isoformat().replace("T", " ")
            print(planinfo)

            cursor.close()

            self.write(
                json.dumps(
                    {"status": "success", "classes": classes, "planinfo": planinfo,},
                    ensure_ascii=False,
                )
            )
            return

        if action == "set_order":
            # 设置课程展示顺序，
            clsids = json.loads(self.get_argument("classids"))
            sid = self.get_argument("sid")
            clsids = [int(id) for id in clsids]
            clsids = json.dumps(clsids)
            sql = "update student set clsids = %s where studentid = %s "
            cursor = util.con.cursor()
            cursor.execute(sql, (clsids, sid))
            cursor.close()
            util.con.commit()

            planid = self.get_argument("pid")
            studentid = self.get_argument("sid")
            order_2nd = self.get_argument("order_2nd")
            order_2nd = util.purge_list(order_2nd.split(","))
            order_2nd = [int(x) for x in order_2nd]
            unified = []
            for id in order_2nd:
                if id not in unified:
                    unified.append(id)
            order_2nd = unified
            order_2nd = [int(x) for x in order_2nd]
            print("备选的顺序是", order_2nd)

            cursor = util.con.cursor()
            sql = "select classid from choice_temp where planid = %s and studentid = %s and is_1st = 0"
            cursor.execute(sql, (planid, studentid))
            sec_ids = list(cursor)
            sec_ids = [int(x[0]) for x in sec_ids]
            print("数据库中的备选id", sec_ids)
            if set(sec_ids) != set(order_2nd):
                dump_err(self, "保存过程中备选顺序和数据库中备选课程不匹配")
                cursor.close()
                return

            sql = "update choice_temp set priority = %s where classid = %s and planid = %s and studentid = %s"
            for ind, id in enumerate(sec_ids):
                cursor.execute(sql, (ind + 5, id, planid, studentid))
                print(cursor.statement)
            util.con.commit()
            cursor.close()
            self.write(json.dumps({"status": "success", "message": "选课计划保存成功"}))
            # 设置备选课程顺序

            return

        if action == "unchoose":
            planid = self.get_argument("pid")
            studentid = self.get_argument("sid")
            classid = self.get_argument("cid")
            courseid = self.get_argument("courseid")

            # 1. 获取要退的课的id
            print(studentid, "正在尝试退", classid)
            cursor = util.con.cursor()
            sql = "select choiceid, is_1st from choice_temp where studentid = %s and classid = %s and planid = %s"
            cursor.execute(sql, (studentid, classid, planid))
            print(cursor.statement)
            choiceid = list(cursor)
            if len(choiceid) == 0:
                dump_err(self, "无法退选自己没选的课")
                cursor.close()
                return

            choiceid, is_1st = choiceid[0]
            print("这个选课记录的id是", choiceid)

            # 2. 如果是首选要求已经没有备选
            if is_1st == 1:
                print("退的是首选的课程")
                sql = "select count(choiceid) from choice_temp where studentid = %s and planid = %s and is_1st = 0"
                cursor.execute(sql, (studentid, planid))
                class_count = list(cursor)[0][0]
                print("备选总数", class_count)
                if class_count != 0:
                    dump_err(self, "有备选的课程时不能退选首选")
                    cursor.close()
                    return

            # 3. 解冻账户冻结金额
            # # 3.1 看看这门课多少钱
            # sql = "select price from course where courseid = %s"
            # cursor.execute(sql, (courseid,))
            # print(cursor.statement)
            # price = list(cursor)[0][0]
            # print("课程费用", price)
            #
            # # 3.2 解冻金额
            # url = util.base_url + "/finance/unfreeze"
            # body = urllib.parse.urlencode({"studentid": studentid, "amount": price})
            # req = tornado.httpclient.HTTPRequest(url, "POST", body=body)
            # res = await tornado.httpclient.AsyncHTTPClient().fetch(req)
            # print("freeze", res.body)

            # 4. 删除课程
            sql = "delete from choice_temp where choiceid = %s"
            cursor.execute(sql, (choiceid,))
            util.con.commit()
            self.write(json.dumps({"status": "success"}))

        if action == "choose":
            # 只有学生能访问
            util.check_role(self, "student")

            # 实际进行选课，谁选什么课程
            sid = self.get_argument("sid")
            cid = self.get_argument("cid")
            is_1st = int(self.get_argument("is_1st"))
            planid = self.get_argument("pid")
            courseid = self.get_argument("courseid")
            print("学生 {} 尝试选 {} 作为 {}".format(sid, cid, is_1st))

            """
            所有的这些检查都要分开做，能切换顺序。提升性能的时候把便宜刷的多的放前面
            1. 判断选课时间是否合法
            2. 检查这个教学班是不是已经选满
            3. 检查这个学生这门课是不是选了其他班级
            4. 检查是不是选了超过4门首选
            5. 检查是不是选了超过2门备选
            6. 首选满了才备选
            7. 检查是不是选了先修课

            扣钱 添加记录
            """

            """1. 判断选课时间是否合法"""
            cursor = util.con.cursor()
            sql = "select start_time, end_time from plan where planid = %s"
            cursor.execute(sql, (planid,))
            time_range = list(cursor)
            if len(time_range) != 1:
                print("选课计划不合法", time_range)
                dump_err(self, "提供的选课计划不合法")
                cursor.close()
                return
            time_range = list(time_range[0])
            time_range = [x.isoformat().replace("T", " ") for x in time_range]
            print("选课计划时间", time_range)
            curr_time = util.curr_time()
            print("当前时间", curr_time)
            if curr_time <= time_range[0]:
                dump_err(self, "还未到选课开始时间")
                cursor.close()
                return
            if curr_time > time_range[1]:
                dump_err(self, "选课已经结束")
                cursor.close()
                return

            """2. 检查首选选这个教学班的是不是已经满了"""
            sql = "select count(choiceid) from choice_temp where is_1st = %s and classid = %s"
            cursor.execute(sql, (is_1st, cid))
            count = list(cursor)[0][0]
            print("当前首选这门课的人数", count)
            if count >= 10:
                dump_err(self, "当前选课人数已经超过10个")
                cursor.close()
                return

            """3. 检查这个学生这门课是不是已经选了这个或者其他班级 """
            sql = "select classid from class where planid = %s and courseid = %s"
            cursor.execute(sql, (planid, courseid))
            classes = list(cursor)
            classes = [x[0] for x in classes]
            print("这门课的教学班id共有", classes)

            sql = "select count(choiceid) from choice_temp where  classid in ("
            sql += "%s, " * len(classes)
            sql = sql[:-2] + ") and planid = %s and studentid = %s"
            classes.append(planid)
            classes.append(sid)
            print(sql)
            cursor.execute(sql, classes)
            class_count = list(cursor)[0][0]
            print("当前学生选了上述班级 {} 次".format(class_count))
            if class_count != 0:
                dump_err(self, "已经选择了这个教学班或者这门课的其他教学班")
                cursor.close()
                return

            """4. 如果首选，检查是不是选了超过4门首选"""
            sql = "select count(choiceid) from choice_temp where studentid = %s and is_1st = 1"
            cursor.execute(sql, (sid,))
            pri_class_count = list(cursor)[0][0]
            print("学生当前共选了 {} 门首选".format(pri_class_count))
            if is_1st == 1:
                if pri_class_count >= 4:
                    dump_err(self, "不能选超过4门首选")
                    cursor.close()
                    return

            """5. 如果备选, 检查是否选了超过2门备选 """
            if is_1st == 0:
                print("choosing 2nd, now chosen", pri_class_count)
                if pri_class_count != 4:
                    dump_err(self, "首选没选满4门课不能选择备选")
                    cursor.close()
                    return

                sql = "select count(choiceid) from choice_temp where studentid = %s and is_1st = 0"
                cursor.execute(sql, (sid,))
                class_count = list(cursor)[0][0]
                print("学生当前共选了 {} 门备选")
                if class_count >= 2:
                    dump_err(self, "不能选超过2门备选")
                    cursor.close()
                    return

            """6. 检查是否选了先修课 """

            """7. 尝试冻结金额"""
            # sql = "select price from course where courseid = %s"
            # cursor.execute(sql, (courseid,))
            # print(cursor.statement)
            # price = list(cursor)[0][0]
            # print("课程费用", price)
            #
            # url = util.base_url + "/finance/freeze"
            # body = urllib.parse.urlencode({"studentid": sid, "amount": price})
            # req = tornado.httpclient.HTTPRequest(url, "POST", body=body)
            # res = await tornado.httpclient.AsyncHTTPClient().fetch(req)
            # print("freeze", res.body)

            """ 在choicetemp表中添加选课记录 """
            print("is 1st", is_1st)
            if is_1st == 1:
                priority = 1
            else:
                priority = 0
            sql = "INSERT INTO `choice_temp`(`studentid`,`classid`,`planid`,`is_1st`, `priority`)VALUES(%s, %s, %s, %s, %s)"
            cursor.execute(sql, (sid, cid, planid, is_1st, priority))
            cursor.close()
            util.con.commit()

            self.write(json.dumps({"status": "success", "message": "选课成功"}))

    def get_classes(self):
        cursor = util.con.cursor()
        sql = "select * from class where planid = %s"
        cursor.execute(sql, (self.get_argument("planid"),))
        classes = list(cursor)
        cursor.close()
        print(self.get_argument("planid"), "的所有课程有", classes)
        for ind in range(len(classes)):
            classes[ind] = list(classes[ind])
        return classes


class Finance(BaseHandler):
    # PLAN: 这里貌似不能加role限制，因为是本机访问，也没有cookie
    def post(self, action):
        if action == "tuition":
            studentid = self.get_argument("studentid")
            amount = self.get_argument("amount")
            message = self.get_argument("message")
            amount = Decimal(amount)
            cursor = util.con.cursor()
            sql = "select frozen from finance where studentid = %s"
            cursor.execute(sql, (studentid,))
            print(cursor.statement)
            frozen = list(cursor)[0][0]
            print("{} 的冻结金额是 {}".format(studentid, frozen))
            if frozen < amount:
                dump_err(self, "账户冻结金额 {} 小于扣费金额 {}".format(frozen, amount))
                cursor.close()
                return

            """扣钱"""
            frozen -= amount
            sql = "update finance set frozen = %s where studentid = %s"
            cursor.execute(sql, (frozen, studentid))
            print(cursor.statement)

            """添加交易记录"""
            sql = "insert into transaction (studentid, amount, comment) values (%s, %s, %s)"
            cursor.execute(sql, (studentid, amount, message))
            print(cursor.statement)
            util.con.commit()
            cursor.close()
            self.write(json.dumps({"status": "success", "message": "学费扣费成功"}, ensure_ascii=False))
            return

        if action == "freeze":
            studentid = self.get_argument("studentid")
            amount = Decimal(self.get_argument("amount"))

            """检查余额"""
            cursor = util.con.cursor()
            sql = "select balance,frozen from finance where studentid = %s"
            cursor.execute(sql, (studentid,))
            print(cursor.statement)
            balance, frozen = list(cursor)[0]
            print("用户的余额和冻结金额是", balance, frozen)
            if balance < amount:
                dump_err(self, "余额不足，请充值后重试冻结")
                cursor.close()
                return

            balance -= amount
            frozen += amount
            sql = "update finance set balance = %s, frozen = %s where studentid = %s"
            cursor.execute(sql, (balance, frozen, studentid))
            util.con.commit()
            cursor.close()
            self.write(json.dumps({"status": "success", "message": "冻结余额成功"}, ensure_ascii=False))
            return

        if action == "unfreeze":
            studentid = self.get_argument("studentid")
            amount = Decimal(self.get_argument("amount"))

            """检查冻结金额"""
            cursor = util.con.cursor()
            sql = "select balance,frozen from finance where studentid = %s"
            cursor.execute(sql, (studentid,))
            print(cursor.statement)
            balance, frozen = list(cursor)[0]
            print("用户的余额和冻结金额是", balance, frozen)
            if frozen < amount:
                dump_err(self, "冻结金额不足，不能解冻这么多")
                cursor.close()
                return

            frozen -= amount
            balance += amount
            sql = "update finance set balance = %s, frozen = %s where studentid = %s"
            cursor.execute(sql, (balance, frozen, studentid))
            util.con.commit()
            cursor.close()
            self.write(json.dumps({"status": "success", "message": "解冻余额成功"}, ensure_ascii=False))
            return
