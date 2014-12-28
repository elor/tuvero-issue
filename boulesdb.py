#!/usr/bin/env python
# -*- coding: utf-8 -*-

import webapp2
import urllib
from google.appengine.api import users
from google.appengine.ext import ndb
from time import sleep
from github import GitHub

class Player(ndb.Model):
    name = ndb.StringProperty()
    modified = ndb.DateTimeProperty(auto_now=True)

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
    query = GitHubCredentials.query().order(Player.modified)
    entries = query.fetch(10)
    if len(entries) > 1:
        # TODO send email or something...
        for entry in entries:
            entry.key.delete()
        entries = []
    if len(entries) == 0:
        return GitHubCredentials(owner='', repo='', token='')

    return entries[0]

NONAME = "nobody"

def player_key(name=NONAME):
    return ndb.Key('Player', name)

def getPlayers():
    players = []
    allplayers_query = Player.query().order(Player.name)
    # 10000 is an arbitrary threshold
    allplayers = allplayers_query.fetch(10000)
    for player in allplayers:
        players.append(player.name.encode('utf-8'))
    return players

class JSONPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        self.response.headers['Access-Control-Allow-Credentials'] = 'true'
        self.response.headers['Access-Control-Allow-Methods'] = 'GET, POST'
        self.response.headers['Access-Control-Allow-Headers'] = 'x-requested-with, x-requested-by'
        self.response.write('["%s"]'%'", "'.join(getPlayers()))

class TxtPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        self.response.write('\n'.join(getPlayers()))

# add new players
EDIT_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8"
<title>edit player names</title>
</head>
<body>
<div>
Spieler:<br>
%s
</div>
<br>
<form action="/new">Neuer Spieler:<br>
<input placeholder="Spielername" name="playername">
<input type="submit" value="Spieler hinzufügen">
</form>
</body>
</html>
"""

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

class EditPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            if validUser(user):
                self.response.headers['Content-Type'] = 'text/html'
                self.response.write(EDIT_PAGE_TEMPLATE%'<br>'.join(getPlayers()))
            else:
                self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
                self.response.write("No write access for user %s"%user.email())
        else:
            self.redirect(users.create_login_url(self.request.uri))

class PlayerEntry(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
        else:
            if validUser(user):
                playername = self.request.get('playername')
                
                # TODO verifications
                playername = playername.replace('"', '')
                
                player = Player(key=player_key(playername))
                player.name = playername;
                player.put()
                
                query_params = {'added': playername.encode('utf-8')}
                self.redirect('/')
            else:
                self.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
                self.response.write("No write access for user %s"%user.email())

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
<title>Boules - Fehler melden</title>
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
                <h1>Boules Turnierverwaltung - Fehler melden</h1>
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
    ('/json', JSONPage),
    ('/txt', TxtPage),
    ('/text', TxtPage),
    ('/plain', TxtPage),
    ('/raw', TxtPage),
    ('/', EditPage),
    ('/new', PlayerEntry),
    ('/issue', IssuePage),
    ('/githubsettings', CredentialsUpdate)
], debug=True)
