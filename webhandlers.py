# coding:utf-8
import json
import traceback
import urllib
from urlparse import urljoin

from lxml import html
from hashlib import md5

from tornado.web import RequestHandler


class BaseHandler(RequestHandler):
    @property
    def redis(self):
        return self.application.redis

    def get_session(self, domain):
        return self.application.sessions[domain]

    def domain_registry(self, domain, uid):
        self.redis.set('authed:%s' % domain, uid)
        self.redis.expire('authed:%s' % domain, 3600)

    def auth_refresh(self, domain):
        uid = self.redis.exists('authed:%s' % domain)
        if uid:
            self.redis.set('authed:%s' % domain, uid)

    @property
    def authed(self):
        return {k.split(':')[1]: self.redis.get(k) for k in self.redis.keys('authed:*')}


class IndexHandler(BaseHandler):
    def get(self):
        self.render("index.html", authed=self.authed)


class LoginHandler(BaseHandler):
    def post(self):
        domain = self.get_argument("d")
        uid = self.get_argument("uid")
        passwd = self.get_argument("passwd")
        vcode = self.get_argument("vcode", "")

        if domain == 'liepin':
            session, code = self.login_liepin(uid, passwd)
            if code == 200:
                for key, value in session.cookies.items():
                    self.set_cookie(key, value, domain=".liepin.com")
                    self.domain_registry(domain, uid)
            self.write(str(code))

        if domain == 'zhaopin':
            session, code = self.login_zhaopin(uid, passwd, vcode)
            if code == 200:
                for key, value in session.cookies.items():
                    self.set_cookie(key, value, domain="zhaopin.com")
                    self.domain_registry(domain, uid)
            self.write(str(code))

    def login_liepin(self, uid, passwd):
        session = self.get_session('liepin')
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

    def login_zhaopin(self, uid, passwd, vcode):
        session = self.get_session('zhaopin')
        headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                   "Accept-Encoding": "gzip, deflate",
                   "Accept-Language": "zh-CN,zh;q=0.8,en;q=0.6,zh-TW;q=0.4,ar;q=0.2",
                   "Cache-Control": "max-age=0",
                   "Connection": "keep-alive",
                   #"Content-Length": "60",
                   "Content-Type": "application/x-www-form-urlencoded",
                   #"Host": "rd2.zhaopin.com",
                   #"Origin": "http://rd2.zhaopin.com",
                   #"Referer": "http://rd2.zhaopin.com/portal/myrd/regnew.asp?za=2",
                   "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/39.0.2171.65 Chrome/39.0.2171.65 Safari/537.36"}

        session.headers = headers
        login_url = "http://rd2.zhaopin.com/loginmgr/loginproc.asp?DYWE=Date.parse(new%20Date())"
        login_data = {"username": uid, "password": passwd,
                      "Validate": vcode, "Submit": ""}
        response = session.post(login_url, login_data)
        return session, response.status_code


class ValidCodeHandler(BaseHandler):
    def get(self):
        t = self.get_argument("t")
        session = self.get_session("zhaopin")
        response = session.get("http://rd2.zhaopin.com/s/loginmgr/picturetimestamp.asp?t={}".format(t))
        self.set_header('Content-type', 'Image/Gif; Charset=utf-8')
        self.set_header('Content-length', len(response.content))
        self.write(response.content)


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
            response = session.post(search_url, data, timeout=30)
            root = html.fromstring(response.content)
            total = int(root.xpath("//i[@class='text-warning']/text()")[0].replace("+", ""))
            trs = root.xpath("//table[@class='table-list']/tbody/tr[contains(@class, 'table-list-peo')]")
            resumes = []
            for tr in trs:
                item = {}
                item['resume_id'] = tr.xpath("./td[1]/input/@data-name")[0]
                item['resume_url'] = tr.xpath("./td[2]/a/@href")[0]
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
        finally:
            self.auth_refresh('liepin')

        result = {'draw': draw, 'recordsFiltered': total,
                  'recordsTotal': total, 'data': resumes}
        self.write(json.dumps(result))


class DetailHandler(BaseHandler):
    def get(self):
        host = "http://h.liepin.com"
        session = self.get_session("liepin")
        response = session.get(urljoin(host, self.request.uri))
        self.write(response.text)


class SearchZhaopinHandler(BaseHandler):
    def get(self):
        keys = self.get_argument("keys")
        page_size = self.get_argument("length", 30)
        start = self.get_argument("start", 0)
        draw = self.get_argument("draw", 1)
        page_num = (int(start)/int(page_size)) + 1

        search_url = "http://rdsearch.zhaopin.com/Home/ResultForCustom"
        search_data = {"SF_1_1_1": keys, "SF_1_1_27": "0",
                       "orderBy": "DATE_MODIFIED,1", "exclude": "1",
                       "pageIndex": page_num}

        try:
            session = self.get_session('zhaopin')
            session.headers["Referer"] = "http://rdsearch.zhaopin.com/Home/SearchByCustom?source=rd"
            get_data = urllib.urlencode(search_data)
            response = session.get("?".join((search_url, get_data)), timeout=30)
            root = html.fromstring(response.content)
            total = int(root.xpath("//div[@class='rd-resumelist-span']/span/text()")[0])
            trs = root.xpath("//form/table/tbody/tr[@valign='top']")
            resumes = []
            for tr in trs:
                item = {}
                item['resume_id'] = tr.xpath("./td[1]/input/@data-smpcvid")[0]
                item['resume_name'] = tr.xpath("./td[1]/input/@resumename")[0]
                item['resume_url'] = tr.xpath("./td[2]/a/@href")[0]
                item['current_title'] = tr.xpath("./td[4]/text()")[0].strip()
                item['edu'] = tr.xpath("./td[5]/text()")[0].strip()
                item['sex'] = tr.xpath("./td[6]/text()")[0].strip()
                item['age'] = tr.xpath("./td[7]/text()")[0].strip()
                item['area'] = tr.xpath("./td[8]/text()")[0].strip()
                item['last_login'] = tr.xpath("./td[9]/text()")[0].strip()
                resumes.append(item)
        except:
            traceback.print_exc()
            total = 0
            resumes = []
        finally:
            self.auth_refresh('zhaopin')

        result = {'draw': draw, 'recordsFiltered': total,
                  'recordsTotal': total, 'data': resumes}
        self.write(json.dumps(result))


class DetailZhaopinHandler(BaseHandler):
    def get(self):
        durl = self.get_argument('durl')
        session = self.get_session("zhaopin")
        response = session.get(durl)
        self.write(response.text)


class LogoutHandler(BaseHandler):
    def get(self):
        domain = self.get_argument('d')
        session = self.get_session(domain)
        if domain == 'liepin':
            logout_url = "http://www.liepin.com/user/logout/"
        if domain == 'zhaopin':
            logout_url = "http://rd2.zhaopin.com/s/loginmgr/logout.asp"

        response = session.get(logout_url)
        self.redis.delete('authed:%s' % domain)
        self.write(str(response.status_code))

if __name__ == "__main__":
    login_liepin("86908584@qq.com", "mengwei802")
