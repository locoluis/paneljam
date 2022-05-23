from bs4 import BeautifulSoup
import requests
import pystache
import sys, re, os
import time
from getpass import getpass

class PanelJam:
	pages_re = re.compile(r'^.*page=([0-9]+)$')
	din_re = re.compile(r'^Drawing in (.*) by ([^ ]*)$', re.S)
	jp_re = re.compile(r'^/jams/([0-9]+)/panels/')
	alt_re = re.compile(r'^(.*) - Online Drawing Game Comic Strip Panel by (.*)$', re.S)

	template = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{title}}</title>
  <style type="text/css">
* {
	box-sizing: border-box;
}
.panel {
	width: 100%;
	max-width: 600px;
}
  </style>
</head>
<body>
  <h1><a href="{{url}}" target="_blank">{{title}}</a></h1>
  <h2>Panels</h2>
  {{#panels}}
  <p>
    <a href="https://www.paneljam.com/{{author}}" target="_blank">By {{author}}</a><br>
    {{#is_nsfw}}<b>NSFW</b><br>{{/is_nsfw}}
    <img class="panel" src="{{image}}" alt="{{alt}}">
  </p>
  {{/panels}}
  <h2>Comments</h2>
  {{#comments}}
  <p>
    <b><a href="https://www.paneljam.com/{{author}}" target="_blank">By {{author}}</a></b><br>
    {{comment}}
  </p>
  {{/comments}}
</div>
</body>
</html>
"""
	user_template = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{user}}</title>
  <style type="text/css">
* {
	box-sizing: border-box;
}
html, body {
	margin: 0;
	width: 100%;
	height: 100%;
	overflow: hidden;
}
body {
	display: grid;
	grid-template-columns: 1fr 690px;
}
#left, #right {
	height: 100%;
}
#left {
	overflow: auto;
}
#right iframe {
	border: 0;
	width: 100%;
	height: 100%;
}
  </style>
</head>
<body>
  <div id="left">
    <h1>{{user}}</h1>
    <h2>Completed Jams</h2>
    <ul>
    {{#jams}}
      <li>
        <a href="../jams/{{number}}/index.html" target="jam">{{title}}</a>
      </li>
    {{/jams}}
    </ul>
    <h2>Jams in Progress</h2>
    <ul>
    {{#progress}}
      <li>
        <a href="../jams/{{number}}/index.html" target="jam">{{title}}</a>
      </li>
    {{/progress}}
    </ul>
  </div>
  <div id="right">
    <iframe name="jam" src="about:blank"></iframe>
  </div>
</body>
</html>
"""
	def __init__(self, user):
		self.pagecount = None
		self.completed = {}
		self.progress = {}
		self.user = user
		self.sess = requests.Session()
		if not os.path.exists("jams"):
			os.mkdir("jams", 0o755)
		if not os.path.exists("players"):
			os.mkdir("players", 0o755)

	def get_page(self, page=1):
		if page == 'progress':
			url = "https://www.paneljam.com/%s/progress/" % (self.user,)
		else:
			url = "https://www.paneljam.com/%s/?page=%d" % (self.user, page)
		res = self.sess.get(url)
		html_doc = res.text
		soup = BeautifulSoup(html_doc, "html.parser")
		if self.pagecount is None and page != 'progress':
			try:
				m = self.pages_re.match(soup.select('span.last a')[0]['href'])
				self.pagecount = int(m.group(1))
			except:
				print(url)
				print(html_doc)
				sys.exit(-1)
		for jam in soup.select('.strip-preview-click'):
			alt = ""
			image = ""
			try:
				m = self.din_re.match(jam.select('img.panel-render')[0]['alt'])
				if m:
					alt = m.group(1)
					image = jam.select('img.panel-render')[0]['src']
			except IndexError as e:
				m = jam.select('.nsfw-panel')
				if m:
					alt = '[NSFW]'
			d = {
				"link": jam['href'],
				"image": image,
				"title": alt
			}
			m = self.jp_re.match(d["link"])
			d["number"] = int(m.group(1))
			m = self.jp_re.match(jam["href"])
			if page == 'progress':
				self.progress[m.group(1)] = d
			else:
				self.completed[m.group(1)] = d
	
	def download_jam(self, jam):
		path = "jams/%d" % (jam["number"])
		if not os.path.exists(path):
			os.mkdir(path)
		print("Downloading https://www.paneljam.com%s" % (jam["link"],))
		res = self.sess.get("https://www.paneljam.com%s" % (jam["link"],))
		panels = []
		comments = []
		if res.status_code == 200:
			html_doc = res.text
			soup = BeautifulSoup(html_doc, "html.parser")
			try:
				title = soup.select('h1 a.glow-text-red')[0].get_text()
			except:
				print("Error https://www.paneljam.com%s" % (jam["link"],))
				print(soup)
				return
			i = 0
			for panel in soup.select('.panel-wrap'):
				is_nsfw = panel.select('.nsfw-panel')
				alt = ""
				author = ""
				if is_nsfw:
					if not os.path.exists(path + "/%03d.png" % (i,)):
						print("https://www.paneljam.com%s - panel %d has been marked as NSFW - please download it manually as %s/%03d.png" % (jam["link"], i, path, i))
						alt = "[NSFW]"
				else:
					if not os.path.exists(path + "/%03d.png" % (i,)):
						ir = self.sess.get(panel.select('img')[0]['src'])
						if ir.status_code == 200:
							f = open(path + "/%03d.png" % (i,), "wb")
							f.write(ir.content)
							f.close()
					alt = panel.select('img')[0]['alt']
					m = self.alt_re.match(alt)
					if m:
						alt = m.group(1)
						author = m.group(2)
				panels.append({
				"image": "%03d.png" % (i,),
				"alt": alt,
				"author": author,
				"is_nsfw": bool(is_nsfw or panel.select(".nsfw-reveal"))
				})
				i += 1
			i = 0
			for panel in soup.select('#view-notes .group'):
				panels[i]['author'] = panel.select('.number > a')[0]['title']
				panels[i]['alt'] = panel.select('p')[0].get_text()
				i += 1
			for panel in soup.select('.comments-box .group'):
				comments.append({
				"author": panel.select('a strong')[0].get_text(),
				"comment": panel.select('p > p')[0].get_text()
				})
		else:
			# This jam has been claimed, we can't download it...
			ir = self.sess.get(jam["image"])
			if ir.status_code == 200:
				if not os.path.exists(path + "/000.png"):
					f = open(path + "/000.png", "wb")
					f.write(lr.content)
					f.close()
			title = jam["title"]
			panels = [{
			"image": "001.png",
			"author": self.user,
			"alt": title
			}]
		
		f = open(path + "/index.html", "wt")
		f.write(pystache.render(self.template, {
			"url": "https://www.paneljam.com%s" % (jam["link"],),
			"title": title,
			"panels": panels,
			"comments": comments
		}))
		f.close()
	
	def process(self):
		self.get_page()
		for i in range(2, self.pagecount + 1):
			self.get_page(i)
		self.get_page('progress')
		for jam in self.completed.values():
			self.download_jam(jam)
		for jam in self.progress.values():
			self.download_jam(jam)
		f = open("players/%s.html" % (self.user,), "wt")
		f.write(pystache.render(self.user_template, {
			"user": self.user,
			"jams": self.completed.values(),
			"progress": self.progress.values()
		}))
		f.close()

	def login(self, login, password):
		res = self.sess.get("https://www.paneljam.com/users/sign_in/")
		html_doc = res.text
		soup = BeautifulSoup(html_doc, "html.parser")
		post_data = {}
		for h in soup.select('form#new_user input[type=hidden]'):
			post_data[h['name']] = h['value']
		post_data['user[email]'] = login
		post_data['user[password]'] = password
		res = self.sess.post("https://www.paneljam.com/users/sign_in/", data=post_data)
		if res.status_code == 200 and "View Profile" in res.text:
			print("Logged in successfully")

if __name__ == '__main__':
	if len(sys.argv) == 1:
		print("Usage: python3 %s [-l] username")
		print("-l: ask for an user e-mail and password (to be able to download NSFW panels)")
		print("username: the username of the player for which jams will be downloaded")
		sys.exit(-1)
	user = sys.argv[1]
	login = False
	if len(sys.argv) > 2 and user == '-l':
		user = sys.argv[2]
		login = True
	panelJam = PanelJam(user)
	if login:
		login = input("Username or E-mail address: ")
		password = getpass("Password: ")
		panelJam.login(login, password)
	panelJam.process()
