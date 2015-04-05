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
<style>

body {
        text-align: center;
}

input[type=text],textarea {
text-align: left;
min-height: 34px;
width: 40em;
padding: 7px 8px;
font-size: 13px;
color: #333;
background-color: #fff;
border: 1px solid #ccc;
border-radius: 3px;
outline: none;
box-shadow: inset 0 1px 2px rgba(0,0,0,0.075)
}

input[type=text][name=title] {
font-size: 16px;
width: 32.5em;
}


input[type=submit] {
margin: 5px;
min-height: 34px;
font-size: 16px;
background-color: #3f3;
border-radius: 3px;
border-color: #5ca941;
border-width: 1px;
text-shadow: rgba(0, 0, 0, 0.247059) 0px -1px 0px;
cursor: pointer;
background-color: rgb(96, 176, 68);
background-image: linear-gradient(rgb(138, 221, 109), rgb(96, 176, 68));
color: white;
font-weight: bold;
padding: 7px 12px;
}

</style>
</head>
<body>
<form action='%s' method="POST" enctype="multipart/form-data">
                <h1>Tuvero Turnierverwaltung - Fehler melden</h1>
                <input name="title" type="text" placeholder="Titel" /><br>
                Bitte beschreiben sie das Problem<br>
                <textarea rows="10" name="message" type="text" placeholder="Beschreibung"/></textarea><br>
                <input name="version" type="text" placeholder="Version (erwünscht)" /><br>
                <input name="user" type="text" placeholder="Benutzer (optional)" /><br>
                Anhang (optional, z.B. für Speicherstände):<br>
                <input name="save" type="file" /><br>
                <input type="submit" value="Fehlerbericht abschicken"/>
</form>
</body>
</html>
                """%self.request.uri)
        
    def post(self):
        try:
            message = {
                'title': self.request.POST['title'],
                'user': self.request.POST['user'],
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
