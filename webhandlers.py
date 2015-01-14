# coding:utf-8
import json
import traceback

from lxml import html
from hashlib import md5

import requests

from tornado.web import RequestHandler


def login_liepin(uid, passwd):
    session = requests.Session()
    headers = {"Accept": "application/json, text/javascript, */*; q=0.01",
               "Accept-Encoding": "gzip, deflate",
               "Accept-Language": "zh-CN,zh;q=0.8,en;q=0.6,zh-TW;q=0.4,ar;q=0.2",
               "Connection": "keep-alive",
               #"Content-Length": "143",
               "Content-Type": "application/x-www-form-urlencoded",
               #"Host": "www.liepin.com",
               #"Origin": "http://www.liepin.com",
               #"Referer": "http://www.liepin.com/",
               "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/39.0.2171.65 Chrome/39.0.2171.65 Safari/537.36",
               "X-Requested-With": "XMLHttpRequest"}

    session.headers = headers
    login_url = "http://www.liepin.com/user/ajaxlogin/"
    login_data = {"isMd5": "2", "user_kind": "2",
                  "layer_from": "wwwindex_rightbox_new",
                  "user_login": uid, "user_pwd": md5(passwd).hexdigest(),
                  "chk_remember_pwd": "on"}

    response = session.post(login_url, login_data)
    return session, response.status_code


def login_zhilian(uid, passwd):
    pass


class BaseHandler(RequestHandler):
    def get_session(self, domain):
        return self.application.authed_user.get(domain)

    def domain_registry(self, domain, session):
        self.application.authed_user[domain] = session

    @property
    def authed(self):
        return self.application.authed_user


class IndexHandler(BaseHandler):
    def get(self):
        self.render("index.html", authed=self.authed)


class LoginHandler(BaseHandler):
    def post(self):
        domain = self.get_argument("d")
        uid = self.get_argument("uid")
        passwd = self.get_argument("passwd")

        if domain == 'liepin':
            session, code = login_liepin(uid, passwd)
            if code == 200:
                for key, value in session.cookies.items():
                    self.set_cookie(key, value, domain=".liepin.com")
                    self.domain_registry(domain, session)
            self.write(str(code))


class SearchHandler(BaseHandler):
    def get(self):
        keys = self.get_argument("keys")
        page_size = self.get_argument("length", 30)
        start = self.get_argument("start", 0)
        draw = self.get_argument("draw", 1)
        page_num = (int(start)/int(page_size)) + 1

        search_url = "http://h.liepin.com/cvsearch/soResume/"
        data = {"form_submit": "1", "keys": keys,
                "titleKeys": "", "company": "",
                "company_type": "0", "industrys": "",
                "jobtitles": "", "dqs": "", "wantdqs": "",
                "workyearslow": "", "workyearshigh": "",
                "edulevellow": "", "edulevelhigh": "",
                "agelow": "", "agehigh": "", "sex": "",
                "sortflag": "12", "expendflag": "1",
                "pageSize": page_size, "curPage": int(page_num)-1}

        try:
            session = self.get_session("liepin")
            response = session.post(search_url, data)
            root = html.fromstring(response.content)
            total = int(root.xpath("//i[@class='text-warning']/text()")[0].replace("+", ""))
            trs = root.xpath("//table[@class='table-list']/tbody/tr[contains(@class, 'table-list-peo')]")
            resumes = []
            for tr in trs:
                item = {}
                item['resume_id'] = tr.xpath("./td[1]/input/@data-name")[0]
                item['sex'] = tr.xpath("./td[3]/text()")[0].strip()
                item['age'] = tr.xpath("./td[4]/text()")[0].strip()
                item['edu'] = tr.xpath("./td[5]/text()")[0].strip()
                item['years'] = tr.xpath("./td[6]/text()")[0].strip()
                item['area'] = tr.xpath("./td[7]/text()")[0].strip()
                item['current_title'] = tr.xpath("./td[8]/@title")[0].strip()
                item['current_company'] = tr.xpath("./td[9]/@title")[0].strip()
                item['last_login'] = tr.xpath("./td[10]/text()")[0].strip()
                resumes.append(item)
        except:
            traceback.print_exc()
            total = 0
            resumes = []

        result = {'draw': draw, 'recordsFiltered': total,
                  'recordsTotal': total, 'data': resumes}
        self.write(json.dumps(result))

if __name__ == "__main__":
    login_liepin("86908584@qq.com", "mengwei802")
