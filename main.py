#!/usr/bin/env python
# -*- coding: utf-8 -*-

import webapp2
import urllib
from google.appengine.api import users
from google.appengine.ext import ndb
from time import sleep
from github import GitHub

class GitHubCredentials(ndb.Model):
    owner = ndb.StringProperty()
    repo = ndb.StringProperty()
    token = ndb.StringProperty()
    modified = ndb.DateTimeProperty(auto_now=True)

def set_githubcredentials(owner, repo, token):
    creds = get_githubcredentials()
    if owner:
        creds.owner = owner
    if repo:
        creds.repo = repo
    if token:
        creds.token = token
    creds.put()

def get_githubcredentials():
    query = GitHubCredentials.query()
    entries = query.fetch(10)
    if len(entries) > 1:
        # TODO send email or something...
        for entry in entries:
            entry.key.delete()
        entries = []
    if len(entries) == 0:
        return GitHubCredentials(owner='', repo='', token='')

    return entries[0]

def validUser(user):
#    if user.email() == "ebriigisto@gmail.com":
    if user:
        return True
    else:
        return False

def validAdmin(user):
    if users.is_current_user_admin():
        return True
    else:
        return False

class CredentialsUpdate(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
        else:
            if validAdmin(user):
                creds = get_githubcredentials()

                self.response.write("""
<form action='%s' method="POST">
                Github Repository Owner: <input name="github_owner" type="text" value="%s" /><br>
                Github Repository Name: <input name="github_repo" type="text" value="%s" /><br>
                Github Access Token (always hidden): <input name="github_token" type="text" placeholder="access token" /><br>
                <input type="submit" />
</form>
                """%(self.request.uri, creds.owner, creds.repo))

                hasAccess = False
                ghcreds = get_githubcredentials()
                gh = GitHub(creds.owner, creds.repo, creds.token)
                try:
                    hasAccess = gh.hasPushAccess()
                except:
                    pass
                
                if hasAccess:
                    self.response.write("<p>Push Access Granted by GitHub.com</p>")
                else:
                    self.response.write("<p>WARNING: No push access with the stored token and repo information. Please provide valid information</p>")
                

            else:
                self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
                self.response.write("No write access for user %s"%user.email())

    def post(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
        else:
            if validAdmin(user):
                try:
                    owner = self.request.POST['github_owner']
                    repo = self.request.POST['github_repo']
                    token = self.request.POST['github_token']

                    set_githubcredentials(owner, repo, token)

                    sleep(1)

                    self.redirect(self.request.uri)
                except:
                    self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
                    self.response.write("No write access for user %s"%user.email())
            else:
                self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
                self.response.write("No write access for user %s"%user.email())

class IssuePage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            username = 'anonymous'
        else:
            username = user.nickname()

        self.response.write("""
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8" />
<title>Tuvero - Fehler melden</title>
</head>
<link rel="stylesheet" href="css/primer.css" />
<link rel="stylesheet" href="css/issue.css" />
<body>
<form action='%s' method="POST" enctype="multipart/form-data">
<h1>Tuvero - Fehler melden</h1>
<p>
Für eine Liste aller gemeldeten Fehler und Verbesserungsvorschläge, siehe <a href="https://github.com/elor/tuvero/issues">https://github.com/elor/tuvero/issues</a>.
</p>
<p>
<input name="title" type="text" placeholder="Titel (z.B. 'Ranking-Tab: leere Spalten bei KO-Turnier')" />
</p>
<h3>Ausführliche Problembeschreibung</h3>
<textarea rows="10" name="message" type="text" placeholder="Ausführliche Beschreibung des Problems:
Wie äußert sich der Fehler?
Wie kann ich den Fehler hervorrufen?"/></textarea>
<h3></h3>
<p>
<input name="version" type="text" placeholder="Version (erwünscht, z.B. '1.4.8')" />
<input name="browser" type="text" placeholder="Betroffene Browser (erwünscht, z.B. 'Google Chrome')" />
<input name="user" type="text" placeholder="Benutzer (optional, z.B. 'Fabe')" />
</p>
<p>
Turnierstand anhängen (optional., z.B. 'boule.json'):
<br>
<input name="save" type="file" />
</p>
<p>
<input class="btn btn-primary" type="submit" value="Fehlerbericht abschicken"/>
</p>
</form>
</body>
</html>
"""%self.request.uri)
        
    def post(self):
        try:
            message = {
                'title': self.request.POST['title'],
                'user': self.request.POST['user'],
                'browser': self.request.POST['browser'],
                'message': self.request.POST['message'],
                'version': self.request.POST['version'],
            }
        except KeyError as err:
            self.response.status = 400
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write('Missing Key: "%s"'%err.message)
            return

        if not message['title']:
            self.response.status = 400
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write('Der Titel der Fehlermeldung wurde nicht angegeben')
            return

        if not message['message']:
            self.response.status = 400
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write('Die Beschreibung der Fehlermeldung wurde nicht angegeben')
            return
            

        # savedata: data from the save button
        try:
            savedata = self.request.POST['save']
            savefilename = savedata.filename
            savedata = savedata.file.read()
        except:
            savefilename = None
            savedata = None


        try:
            ghcreds = get_githubcredentials()
        except:
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write('Missing Key: "%s"'%err.message)
            return

        gh = GitHub(ghcreds.owner, ghcreds.repo, ghcreds.token)
        url = ''
        try:
            url = gh.createIssue(message, savedata, savefilename)
        except:
            pass

        if url:
            # everything's fine
#            self.response.status = 201
#            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
#            self.response.write(url)
            self.redirect(url.encode('ascii', 'ignore'))
        else:
            self.response.status = 500
            self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
            self.response.write("Server Error: cannot create issue. This might be caused by missing or invalid values")

class PubKeyPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        self.response.write("TODO: read pubkey from database or generate a disposable one")

application = webapp2.WSGIApplication([
    ('/', IssuePage),
    ('/settings', CredentialsUpdate)
], debug=True)
