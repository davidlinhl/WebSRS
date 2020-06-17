import tornado.web
import json
import tornado.httpclient
import urllib
import json
from util import BaseHandler, con, max_student_per_class, dump_err
import util
from decimal import *


class JTBase(BaseHandler):
    @tornado.web.authenticated
    def post(self, action):
        role = self.get_secure_cookie("role")
        if role != b"admin":
            dump_err(self, "无权访问此接口")

        if action == "list":
            cursor = con.cursor()
            cursor.execute("select * from {}".format(self.table_name))
            print("list:", cursor.statement)
            records = []
            for data in cursor:
                data_dict = {}
                for ind in range(len(self.col_names)):
                    data_dict[self.col_names[ind]] = str(data[ind])
                records.append(data_dict)
            cursor.close()
            print("list records", records)

            result = {}
            result["Result"] = "OK"
            result["Records"] = records
            print(json.dumps(result))
            self.write(json.dumps(result))
            return

        if action == "create":
            data = [self.get_argument(col_name) for col_name in self.col_names[1:]]
            print("create paramaters", data)
            cursor = con.cursor()
            names = ""
            for name in self.col_names[1:-1]:
                names += name + ","
            names += self.col_names[-1]
            query = (
                "insert into {} ("
                + names
                + ") values ("
                + "%s," * (len(self.col_names) - 2)
                + "%s"
                + ")"
            ).format(self.table_name)
            cursor.execute(query, data)
            print(cursor.statement)
            new_id = cursor.lastrowid
            """ 添加一个默认密码 """
            sql = "insert into passwd values (%s, %s, %s, %s)"
            if self.table_name == "teacher":
                username = util.get_pinyin(data[0]) + data[9].split("-")[0][-2:]
            else:
                username = util.get_pinyin(data[0]) + data[6].split("-")[0][-2:]
            cursor.execute(
                sql, (username, util.get_md5(util.default_password), self.user_type, new_id),
            )
            print("insert passwd:", cursor.statement)
            con.commit()

            """ 如果学生，添加财务记录 """
            if self.user_type == 2:
                sql = "insert into finance values (%s, %s, %s)"
                cursor.execute(sql, (new_id, 10000, 0))
                con.commit()

            print(list(cursor))
            cursor.close()

            result = {}
            result["Result"] = "OK"
            data.insert(0, new_id)
            temp = {}
            for ind in range(len(self.col_names)):
                temp[self.col_names[ind]] = data[ind]
            result["Record"] = temp

            print(json.dumps(result))
            self.write(json.dumps(result))

        if action == "update":
            data = [self.get_argument(col_name) for col_name in self.col_names]
            print("update paramaters", data)

            cursor = con.cursor()
            query = "update {} set ".format(self.table_name)
            for ind, col in enumerate(self.col_names[1:-1]):
                query += col + "= %s,"
            query += self.col_names[-1] + "= %s"
            query += " where " + self.col_names[0] + "= '{}'".format(data[0])
            cursor.execute(query, data[1:])
            print("update: ", cursor.statement)
            con.commit()
            cursor.close()

            result = {}
            result["Result"] = "OK"
            self.write(json.dumps(result))

        if action == "delete":
            key_value = self.get_argument(self.col_names[0])
            print("delete param", key_value)

            cursor = con.cursor()
            # 从密码表中删除记录
            sql = "delete from passwd where userid = %s and user_type = %s"
            cursor.execute(sql, (key_value, self.user_type))
            print(cursor.statement)

            # 从财务表中删除记录
            if self.user_type == 2:
                sql = "delete from finance where studentid = %s"
                cursor.execute(sql, (key_value,))
                print(cursor.statement)

            # 删除学生记录
            query = ("delete from {} where " + self.col_names[0] + " = %s").format(self.table_name)
            cursor.execute(query, [key_value])
            print(cursor.statement)
            con.commit()

            cursor.close()

            result = {}
            result["Result"] = "OK"
            self.write(json.dumps(result))


class EditCourse(BaseHandler):
    table_name = "course"
    col_names = [
        "courseid",
        "name",
        "number",
        "academy",
        "credit",
        "prerequisites",
        "price",
    ]
    # 定义一个所有展示名字的list
    disp_names = [
        "id",
        "课程名",
        "课程编号",
        "学院",
        "学分",
        "先修课",
        "课程学费",
    ]

    @tornado.web.authenticated
    def get(self):
        role = self.get_secure_cookie("role")
        if not util.check_role(self, "admin"):
            return

        print("当前用户role", role)
        self.render(
            "editCourse.html",
            col_names=self.col_names,
            disp_names=self.disp_names,
            primary_key=self.col_names[0],
            role=role,
        )

    @tornado.web.authenticated
    def post(self, action):
        role = self.get_secure_cookie("role")
        if role != b"admin":
            dump_err(self, "无权访问此接口")

        if action == "list":
            cursor = con.cursor()
            cursor.execute("select * from {}".format(self.table_name))
            print("list:", cursor.statement)
            records = []
            for data in cursor:
                data = list(data)
                data[3] = "软件学院"
                data_dict = {}
                for ind in range(len(self.col_names)):
                    data_dict[self.col_names[ind]] = str(data[ind])

                records.append(data_dict)
            cursor.close()
            print("list records", records)

            result = {}
            result["Result"] = "OK"
            result["Records"] = records
            print(json.dumps(result))
            self.write(json.dumps(result))
            return


class EditStudent(JTBase):
    user_type = 2
    table_name = "student"
    col_names = [
        "studentid",
        "name",
        "number",
        "ismale",
        "birth",
        "academyid",
        "class",
        "enroll_year",
        "contact",
        "address",
    ]
    # 定义一个所有展示名字的list
    disp_names = [
        "id",
        "姓名",
        "学号",
        "性别",
        "出生年月",
        "学院",
        "班级",
        "入学年",
        "联系方式",
        "地址",
    ]

    @tornado.web.authenticated
    def get(self):
        role = self.get_secure_cookie("role")
        if not util.check_role(self, "admin"):
            return

        print("当前用户role", role)
        self.render(
            "editstudent.html",
            col_names=self.col_names,
            disp_names=self.disp_names,
            primary_key=self.col_names[0],
            role=role,
        )


class EditTeacher(JTBase):
    user_type = 1
    table_name = "teacher"
    col_names = [
        "teacherid",
        "name",
        "number",
        "ismale",
        "dateofbirth",
        "contact",
        "address",
        "academyid",
        "title",
        "salary",
        "inductiontime",
    ]
    # 定义一个所有展示名字的list
    disp_names = [
        "id",
        "姓名",
        "编号",
        "性别",
        "出生年月",
        "联系方式",
        "家庭住址",
        "学院",
        "职称",
        "薪资",
        "入职时间",
    ]

    @tornado.web.authenticated
    def get(self):
        role = self.get_secure_cookie("role")
        if not util.check_role(self, "admin"):
            return
        self.render(
            "editteacher.html", col_names=self.col_names, disp_names=self.disp_names, role=role,
        )


class StudentViewGrades(BaseHandler):
    disp_names = ["课程编号", "课程名称", "学院", "学分", "班级", "老师", "学期", "成绩"]

    @tornado.web.authenticated
    def get(self):
        role = self.get_secure_cookie("role")
        if role != b"student":
            self.render("error.html", title="您无权查看本页面", message="请使用正确的账户登录")
            return
        userid = self.get_secure_cookie("userid")
        userid = str(userid)[2:-1]

        cursor = con.cursor()
        classidquery = "select classid from registration where studentid = " + userid
        cursor.execute(classidquery)
        print(cursor.statement)
        theclasses = list(cursor)
        print("theclasses", theclasses)
        gradeinfo = []
        gradeinfoquery = (
            "select semester, grade " "from registration as r where r.studentid = " + userid
        )
        cursor.execute(gradeinfoquery)
        print(cursor.statement)
        gradeinfo = list(cursor)
        print("gradeinfo", gradeinfo)

        if len(theclasses) != 0:
            for i in range(len(theclasses)):
                classid = theclasses[i][0]

                baseinfoquery = (
                    "select course.courseid, course.name, course.academyid, credit, classid, teacher.name from course join class join teacher on course.courseid = class.courseid and class.teacherid = teacher.teacherid "
                    "where class.classid = " + str(classid)
                )
                cursor.execute(baseinfoquery)
                print(cursor.statement)
                baseinfo = list(cursor)
                print("baseinfo: ", baseinfo)

                if len(baseinfo) != 0:
                    tmp1 = list(baseinfo[0])
                    tmp2 = list(gradeinfo[i])
                    tmp1 += tmp2
                    gradeinfo[i] = tuple(tmp1)
                    # print(gradeinfo)
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
        print("gradeinfo", gradeinfo)
        for ind in range(len(gradeinfo)):
            gradeinfo[ind] = list(gradeinfo[ind])
            cursor.execute("select name from academy where academyid = %s", (gradeinfo[ind][2],))
            res = list(cursor)[0][0]
            gradeinfo[ind][1] = res
            gradeinfo[ind][6] = grade_names[gradeinfo[ind][6]]
            if gradeinfo[ind][7] == None:
                gradeinfo[ind][7] = "未上分"

        namequery = "select name from student where studentid = " + userid
        cursor.execute(namequery)
        nameinfo = list(cursor)
        print(nameinfo[0][0])
        cursor.close()

        self.render(
            "sGrades.html",
            disp_names=self.disp_names,
            gradeinfo=gradeinfo,
            nameinfo=nameinfo[0][0],
            role=role,
        )


class EndRegistration(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        # 点击结束选课按钮之后：
        # 检查用户权限
        role = self.get_secure_cookie("role")
        print(role)
        if role != b"admin":
            self.render(
                "error.html", title="您没有权限访问此页面", message="只有教务主任可以查看所有选课计划"
            )  # 重定向，如果不是管理员，就跳转了
            return
        # self.end_registration()
        # self.modify_db()
        self.render(
            "endreg.html", role=self.get_secure_cookie("role"), planid=self.get_argument("planid")
        )

    @tornado.web.authenticated
    async def post(self):
        # 检查用户权限
        role = self.get_secure_cookie("role")
        print(role)
        if role != b"admin":
            self.render("error.html", title="您没有权限访问此页面", message="只有教务主任可以查看所有选课计划")
            return

        action = self.get_argument("action")
        if action == "modify":
            await self.modify_db()
            await self.charge()

            return
        if action == "endreg":
            self.end_registration()
            return

    def end_registration(self):
        planid = self.get_argument("planid")
        # 需要删除的课程列表：
        cls_to_del = set()
        choicelist = []
        registration_temp = {}  # 选课情况dict
        # 检查选课计划是不是已经结束
        cursor = con.cursor()
        sql = "select end_time from plan where planid = %s"
        cursor.execute(sql, (planid,))
        end_time = list(cursor)[0][0].isoformat().replace("T", " ")
        print("选课计划结束时间", end_time)
        if util.curr_time() < end_time:
            dump_err(self, "未到选课结束时间不能结束选课")
            return
        # 从choice_temp中选出结束的planid里所有的选课记录

        choicequery = "select * from choice_temp where planid = " + planid
        cursor.execute(choicequery)
        choicelist = list(cursor)
        print("1 ", choicelist)

        if len(choicelist) > 0:
            # 对所有选课记录进行投票统计，如果一个班级首选加备选人数都不超过3个人，这个教学班删除。写入一个set cls_to_del
            clsidsquery = "select distinct classid from choice_temp where planid = " + str(planid)
            cursor.execute(clsidsquery)
            clsids = list(cursor)
            print("2 ", clsids)

            remainnum_per_class = {}
            # 初始化remainnum_perclass
            for i in range(0, len(clsids)):
                remainnum_per_class[clsids[i][0]] = max_student_per_class
            print("3 ", remainnum_per_class)

            for eachchoice in choicelist:
                theclassid = eachchoice[2]
                if remainnum_per_class[theclassid] > 0:
                    remainnum_per_class[theclassid] += -1
            print("4 ", remainnum_per_class)

            for key in remainnum_per_class.keys():  # key=classid
                if remainnum_per_class[key] > max_student_per_class - 3:
                    cls_to_del.add(key)
            print("5 ", cls_to_del)

            # choicelist按照cls_to_del删除记录
            # 第一轮筛选之后的choicelist:
            index = 0
            while index < len(choicelist) and index >= 0:
                # print(index," " ,choicelist)
                if choicelist[index][2] in cls_to_del:
                    # print("hhh",choicelist[index][2])
                    choicelist.remove(choicelist[index])
                    index -= 1
                index += 1
            print("6 ", choicelist)

            if len(choicelist) > 0:
                # 按照首选给每个人选课，生成一个选课情况dict。
                # registration_temp = {}  # 选课情况dict
                # 初始化选课情况字典
                for eachchoice in choicelist:
                    registration_temp[eachchoice[1]] = []
                print("7 ", registration_temp)

                # 重新初始化remainnum_per_class (重复)
                for key in remainnum_per_class.keys():
                    remainnum_per_class[key] = max_student_per_class

                # 按照首选课选到选课情况字典registration_temp里
                for eachchoice in choicelist:
                    if eachchoice[-1] == 1:  # 是首选课
                        this_stu_id = eachchoice[1]
                        this_cls_id = eachchoice[2]
                        registration_temp[this_stu_id].append(this_cls_id)
                        remainnum_per_class[this_cls_id] += -1
                print("8 ", registration_temp)
                print("9 ", remainnum_per_class)

                # #在dict中统计所有班级的人数，如果不够3个人这个班级删除，dict中的记录删除
                # for key in remainnum_per_class.keys():# key=classid
                #     if remainnum_per_class[key] > max_student_per_class-3:
                #         cls_to_del.add(key) # 增加要删除的课id，更新了cls_to_del！！！！！！！！！！！！！！！！
                # print("10 ",cls_to_del)
                #
                # # 在registration_temp里学生的课程列表中，删掉更新后的cls_to_del里面的课id
                # for key in registration_temp.keys():# key=studentid
                #     clsids = registration_temp[key] # 每个学生选的一堆课id 的list
                #     index = 0
                #     while index <len(clsids) and index >= 0 :# 每个学生选的一堆课id中的一个
                #         if clsids[index] in cls_to_del:
                #             print("clsids[index]:",clsids[index])
                #             clsids.remove(clsids[index])
                #             index-=1
                #         index+=1
                #
                # # 上一步操作后registration_temp里学生的课程列表可能是空的了（学生的至多四个首选课全都没选上），需要删除他
                # for key in list(registration_temp.keys()):# key=studentid
                #     if len(registration_temp[key]) == 0: # 这个学生没有选上课，一堆课id删减到为空了(太惨了)
                #         registration_temp.pop(key)
                # print("11 ",registration_temp)
                #
                #
                # # choicelist按照cls_to_del删除记录
                # # 第二轮筛选之后的choicelist:
                # while index < len(choicelist) and index >= 0:
                #     # print(index," " ,choicelist)
                #     if choicelist[index][2] in cls_to_del:
                #         # print("hhh",choicelist[index][2])
                #         choicelist.remove(choicelist[index])
                #         index-=1
                #     index+=1
                # print("12 ",choicelist)

                # 用第一备选给学生补齐选课
                if len(choicelist) > 0:
                    # 找dict中不满4门课的学生。给他选上第一备选。
                    for key in list(registration_temp.keys()):  # key = studentid
                        if len(registration_temp[key]) < 4:  # 找到dict中不满4门课的学生id: key
                            for eachchoice in choicelist:
                                if (
                                    eachchoice[1] == key and eachchoice[-3] == 5
                                ):  # 找到这个学生的第一备选课id：eachchoice[2]
                                    registration_temp[key].append(eachchoice[2])  # 给他选上第一备选
                                    remainnum_per_class[eachchoice[2]] += -1
                                    print("_+_+_+_+_+_+", eachchoice[2])
                    print("$$$$$$$$", registration_temp, "$$$$$$$$$$", remainnum_per_class)

                    # 找dict中还是不满4门课的学生。给他选上第二备选。
                    for key in list(registration_temp.keys()):  # key = studentid
                        if len(registration_temp[key]) < 4:  # 找到dict中不满4门课的学生id: key
                            for eachchoice in choicelist:
                                if (
                                    eachchoice[1] == key and eachchoice[-3] == 6
                                ):  # 找到这个学生的第二备选课id：eachchoice[2]
                                    registration_temp[key].append(eachchoice[2])  # 给他选上第二备选
                                    remainnum_per_class[eachchoice[2]] += -1

                    # 在dict中统计所有班级的人数，如果不够3个人这个班级删除，dict中的记录删除
                    for key in remainnum_per_class.keys():  # key=classid
                        if remainnum_per_class[key] > max_student_per_class - 3:
                            cls_to_del.add(key)  # 增加要删除的课id，更新了cls_to_del！！！！！！！！！！！！！！！！
                    print("10 ", cls_to_del)

                    # 在registration_temp里学生的课程列表中，删掉更新后的cls_to_del里面的课id
                    for key in registration_temp.keys():  # key=studentid
                        clsids = registration_temp[key]  # 每个学生选的一堆课id 的list
                        index = 0
                        while index < len(clsids) and index >= 0:  # 每个学生选的一堆课id中的一个
                            if clsids[index] in cls_to_del:
                                print("clsids[index]:", clsids[index])
                                clsids.remove(clsids[index])
                                index -= 1
                            index += 1

                    # 上一步操作后registration_temp里学生的课程列表可能是空的了（学生的至多四个首选课全都没选上），需要删除他
                    for key in list(registration_temp.keys()):  # key=studentid
                        if len(registration_temp[key]) == 0:  # 这个学生没有选上课，一堆课id删减到为空了(太惨了)
                            registration_temp.pop(key)
                    print("11 ", registration_temp)

                    # choicelist按照cls_to_del删除记录
                    # 第三轮筛选之后的choicelist:
                    while index < len(choicelist) and index >= 0:
                        # print(index," " ,choicelist)
                        if choicelist[index][2] in cls_to_del:
                            # print("hhh",choicelist[index][2])
                            choicelist.remove(choicelist[index])
                            index -= 1
                        index += 1
                    print("12 ", choicelist)

                    # # 用第二备选给学生补齐选课(重复)
                    # if len(choicelist) > 0:
                    #     # 找dict中不满4门课的学生。给他选上第二备选。
                    #     for key in list(registration_temp.keys()):  # key = studentid
                    #         if len(registration_temp[key]) < 4:  # 找到dict中不满4门课的学生id: key
                    #             for eachchoice in choicelist:
                    #                 if (
                    #                     eachchoice[1] == key and eachchoice[-3] == 6
                    #                 ):  # 找到这个学生的第二备选课id：eachchoice[2]
                    #                     registration_temp[key].append(eachchoice[2])  # 给他选上第二备选
                    #                     remainnum_per_class[eachchoice[2]] += -1
                    #
                    #     # 在dict中统计所有班级的人数，如果不够3个人这个班级删除，dict中的记录删除
                    #     for key in remainnum_per_class.keys():  # key=classid
                    #         if remainnum_per_class[key] > max_student_per_class - 3:
                    #             cls_to_del.add(key)  # 增加要删除的课id，更新了cls_to_del！！！！！！！！！！！！！！！！
                    #     print("13 ", cls_to_del)
                    #
                    #     # 在registration_temp里学生的课程列表中，删掉更新后的cls_to_del里面的课id
                    #     for key in registration_temp.keys():  # key=studentid
                    #         clsids = registration_temp[key]  # 每个学生选的一堆课id 的list
                    #         index = 0
                    #         while index < len(clsids) and index >= 0:  # 每个学生选的一堆课id中的一个
                    #             if clsids[index] in cls_to_del:
                    #                 print("clsids[index]:", clsids[index])
                    #                 clsids.remove(clsids[index])
                    #                 index -= 1
                    #             index += 1
                    #
                    #     # 上一步操作后registration_temp里学生的课程列表可能是空的了（学生的至多四个首选课全都没选上），需要删除他
                    #     for key in list(registration_temp.keys()):  # key=studentid
                    #         if len(registration_temp[key]) == 0:  # 这个学生没有选上课，一堆课id删减到为空了(太惨了)
                    #             registration_temp.pop(key)
                    #     print("14 ", registration_temp)
                    #
                    #     # choicelist按照cls_to_del删除记录
                    #     # 第四轮筛选之后的choicelist:
                    #     while index < len(choicelist) and index >= 0:
                    #         # print(index," " ,choicelist)
                    #         if choicelist[index][2] in cls_to_del:
                    #             # print("hhh",choicelist[index][2])
                    #             choicelist.remove(choicelist[index])
                    #             index -= 1
                    #         index += 1
                    #     print("15 ", choicelist)

        # 给主任显示要删除的教学班:需要render现在的cls_to_del
        print("set", cls_to_del)
        cursor.close()
        self.write(
            json.dumps(
                {
                    "status": "success",
                    "planid": planid,
                    "cls_to_del": list(cls_to_del),
                    "choicelist": choicelist,
                    "registration_temp": registration_temp,
                },
                ensure_ascii=False,
            ),
        )

    async def modify_db(self):
        planid = int(self.get_argument("planid"))
        cls_to_del = json.loads(self.get_argument("cls_to_del"))
        registration_temp = json.loads(self.get_argument("registration_temp"))
        choicelist = json.loads(self.get_argument("choicelist"))

        cursor = con.cursor()
        if len(choicelist) > 0:
            print(planid)

            for eachchoice in choicelist:
                # print("wowowowow",eachchoice[4])
                if eachchoice[4] == planid:
                    # print("hhh")
                    # 将实际生效的选课信息写入registration数据库
                    print(eachchoice[2], " ", eachchoice[1])
                    toregquery = (
                        "insert into registration (classid,studentid,grade,semester) values ({},{},NULL,1)"
                    ).format(eachchoice[2], eachchoice[1])
                    cursor.execute(toregquery)
                    # print(cursor.statement)

        # 从choice_temp中删除planid所有的选课记录
        delchoice = ("delete from choice_temp where planid = {}").format(planid)
        cursor.execute(delchoice)
        print(cursor.statement)
        con.commit()

        if len(cls_to_del) > 0:
            # 删除不够人数的教学班
            for eachclass in cls_to_del:
                delclass = ("delete from class where planid = {} and classid = {}").format(
                    planid, eachclass
                )
                cursor.execute(delclass)
                print(cursor.statement)
                con.commit()

        # 先计算每个学生需要扣多少钱，添加扣费记录
        # cursor = con.cursor()
        for key in list(registration_temp.keys()):  # key = studentid
            print("+_+_+", registration_temp[key])
            amount = 0
            sql = "select courseid from class where classid in (" + "%s, " * len(
                registration_temp[key]
            )
            sql = sql[:-2] + ")"
            cursor.execute(sql, registration_temp[key])
            print("_____", cursor.statement)
            courseids = list(cursor)
            print("courseids", courseids)
            courseids = [x[0] for x in courseids]

            print("the courses chose are", courseids)

            sql = "select price from course where courseid in (" + "%s, " * len(courseids)
            sql = sql[:-2] + ")"
            cursor.execute(sql, courseids)
            print(cursor.statement)
            prices = list(cursor)
            print(prices)
            prices = [x[0] for x in prices]
            print(prices)

            theamount = Decimal(0)
            for price in prices:
                theamount += Decimal(price)
                print(theamount)
            print("last:", theamount)

            sql = "insert into charge_queue (studentid, amount, comment) values (%s, %s, %s)"
            cursor.execute(sql, (key, theamount, "选" + str(len(registration_temp[key])) + "门课的费用"))
            con.commit()
        cursor.close()
        # self.charge()
        # print("_++_+_+_")

    async def charge(self):
        cursor = con.cursor()
        # 尝试扣费finance
        chargequery = "select * from charge_queue"
        cursor.execute(chargequery)
        chargelist = list(cursor)
        index = 0
        # print("hhhhhheheheheheh")
        while len(chargelist) > 0 and index < len(chargelist):
            # # 获取该学生当前余额
            # getbalance = ("select balance from finance where studentid = {}").format(chargelist[index][1])
            # cursor.execute(getbalance)
            # balance = list(cursor)

            # # 尝试插入finance
            # insfinance = ("update finance set balance={},frozen=0)").format(balance-chargelist[index][2])
            # cursor.execute(insfinance)

            # 尝试插入finance
            url = util.base_url + "/finance/tuition"
            data = {
                "studentid": chargelist[index][1],
                "amount": chargelist[index][2],
                "message": chargelist[index][3],
            }
            body = urllib.parse.urlencode(data)

            try:
                # 发起一个post请求去请财务的接口
                print("发起一个post请求去请财务的接口")
                req = tornado.httpclient.HTTPRequest(url, "POST", body=body)
                res = await tornado.httpclient.AsyncHTTPClient().fetch(req)
                res = json.loads(res.body)
                # print("res: ",res)

            except:
                # 网络链接错误
                dump_err(self, "网络连接错误")
            else:
                if res["status"] != "success":
                    # 成功
                    return

                delcharge = ("delete from charge_queue where chargeid = {}").format(
                    chargelist[index][0]
                )
                cursor.execute(delcharge)
                index += -1
                print(cursor.statement)

            # 判断扣费是否成功，如果成功，则在charge_queue删除记录
            index += 1

            # 更新一下chargelist
            chargequery = "select * from charge_queue"
            cursor.execute(chargequery)
            chargelist = list(cursor)
            print("index:", index, " new chargelist: ", chargelist)
            # 这里未完成需要有个重置index

            # url = util.base_url + "/finance/tuition"
            # # 获取异步客户端，fetch（url， callback回调）
            # clicent = tornado.httpclient.AsyncHTTPClient()
            # print('异步请求开始')
            # clicent.fetch(url, callback="POST")
            # self.write('请求成功')
        con.commit()
        cursor.close()


"""
1. 结束选课运算 EndRegistration.end_registration
self.write(json.dumps({"status":"success", "del_class_list": del_class_list, "student_choice":student_choice}, ensure_ascii=False))
ret: 删除课程列表，学生选课安排 json.dumpes(arr) html->js

2. 修改数据库 modify_db
self.get_argument("del_class_list")
self.get_argument("student_choice")
json.decode()

删除choice_temp,删除k掉的课，计算学生学费，插入chargequeue
调用self.charge()


3. 扣费 charge
从chargequeue拿待扣费记录，尝试扣费
try res['status'] 检查错误

html
- 页面要鉴权 authenticated, check_role
- 参数要合法 planid 得存在
- 选课计划要已经结束了，不能结束一个正在进行的选课计划
"""
