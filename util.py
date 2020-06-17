import tornado.web
import hashlib
import mysql.connector
import tornado.template
import json
import time
import pypinyin

max_student_per_class = 10
default_password = "111"
# base_url = "http://localhost:8000"
base_url = "https://dxy.zdcd.online:5000"

# print(time.strftime("%Y-%m-%d", time.localtime()))


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("role")


def get_pinyin(name):
    """根据用户的中文名生成英文用户名字符串.
    原来就是英文不处理，
    如果是中文，2个字全拼，3个字或以上第一个字全拼，剩下的首字母

    Parameters
    ----------
    name : 用户名
        纯中文或纯英文.

    Returns
    -------
    type
        拼音字符串.
    """
    # 如果第一个字不是中文，直接返回字符串
    if not ("\u4e00" <= name[0] <= "\u9fff"):
        return name

    pinyin = pypinyin.pinyin(name, style=pypinyin.NORMAL)
    pinyin = [x[0] for x in pinyin]
    print(pinyin)
    name_str = ""
    if len(pinyin) == 2:
        name_str += pinyin[0] + pinyin[1]
    else:
        name_str += pinyin[0]
        for ind in range(1, len(pinyin)):
            name_str += pinyin[ind][0]
    return name_str


def connect():
    cnx = mysql.connector.connect(
        host=host, user=user, passwd=passwd, database=database, auth_plugin="mysql_native_password",
    )
    return cnx


# TODO: 重启服务器con不会重新连接，需要解决
con = connect()
print("Connection established!")


def get_md5(pswd):
    pswd = str(pswd)
    pswd = pswd.strip()
    return hashlib.md5(pswd.encode("utf-8")).hexdigest()


# print(get_md5("test"))


def map_class_time(str):
    times = json.loads(str)
    weekday = ["空", "一", "二", "三", "四", "五", "六", "日"]
    ret = []
    for time in times:
        ret.append("周{}第{}节".format(weekday[int(time[0])], time[1]))
    return ret


# print(map_class_time("[[1, 12], [2, 22]]"))


def purge_list(lst):
    """删除一个list中所有的 ""

    Parameters
    ----------
    lst : type
        Description of parameter `lst`.

    Returns
    -------
    type
        Description of returned object.

    """
    while "" in lst:
        lst.remove("")
    return lst


def check_role(self, desired_role):
    user_role = self.get_secure_cookie("role")
    print(user_role)
    desired_role = str.encode(desired_role)
    if desired_role != user_role:
        self.render("error.html", title="您无权查看本页面", message="请使用正确的账户登录")
        return False
    return True


def curr_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def dump_err(self, msg):
    self.write(json.dumps({"status": "fail", "message": msg}, ensure_ascii=False))


def get_grade(enroll_year):
    """通过学生入学年份和当前时间及月份计算学生已经入学几个学期.
    算法是年做差，乘2，
    -1  (3月)  不动  (9月)  +1
    Parameters
    ----------
    enroll_year : 四位数
        入学年份，默认9月

    Returns
    -------
    type
        当前是学生在校的第几个学期.

    """
    curr_year = time.localtime(time.time()).tm_year
    curr_month = time.localtime(time.time()).tm_mon
    grade = curr_year - enroll_year
    grade *= 2
    if curr_month < 3:
        grade -= 1
    elif curr_month > 9:
        grade += 1
    return grade
