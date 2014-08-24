#!/usr/bin/env python
# -*- coding: utf-8 -*-

import webapp2
import urllib
from google.appengine.api import users
from google.appengine.ext import ndb

class Player(ndb.Model):
    name = ndb.StringProperty()
    modified = ndb.DateTimeProperty(auto_now=True)

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

class DataPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        self.response.write('{players: [%s]}'%', '.join(getPlayers()))

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
    if user.email() == "ebriigisto@gmail.com":
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
                self.response.headers['Content-Type'] = 'text/plain'
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
                
                player = Player(key=player_key(playername))
                player.name = playername;
                player.put()
                
                query_params = {'added': playername.encode('utf-8')}
                self.redirect('/')
            else:
                self.response.headers['Content-Type'] = 'text/plain'
                self.response.write("No write access for user %s"%user.email())

application = webapp2.WSGIApplication([
    ('/json', DataPage),
    ('/', EditPage),
    ('/new', PlayerEntry),
], debug=True)
