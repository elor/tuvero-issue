#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2
import json
import base64
import time

class GitHub:
    def __init__(self, owner, repo, accesskey):
        self.owner = owner
        self.repo = repo
        self.repourl = "repos/%s/%s"%(self.owner, self.repo)
        self._accesskey = accesskey

    def _get(self, url):
        return self._post(url, None)

    def _post(self, url, data):
        baseurl = 'https://api.github.com/'
        print url
        url = baseurl + url
        if data:
            data = json.dumps(data)
        req = urllib2.Request(url, data)
        base64string = base64.encodestring('%s:x-oauth-basic'%self._accesskey).replace('\n', '')
        req.add_header("Authorization", "Basic %s" % base64string)
        response = urllib2.urlopen(req)
        return json.loads(response.read())

    def createGist(self, description, filename, content):
        if not filename:
            filename = 'boules_%s.json'%time.strftime('%F_%X')
        if not description:
            description = 'No Description'

        postdata = {
            'description': description,
            'public': True,
            'files': {
                filename: {
                    'content': content,
                    }
            },
        }

        return self._post('gists', postdata)['url']

    def formatIssue(self, message):
        text = message['message']
        if not text:
            text = 'No bug description given'
        text = text.strip() + '\n\n'

        try:
            if message['version']:
                text += 'Version: %s\n'%message['version']
        except:
            pass

        try:
            if message['user']:
                text += 'User: %s\n'%message['user']
        except:
            pass

        try:
            if message['saveurl']:
                text += 'Save File URL: %s\n'%message['saveurl']
        except:
            pass

        text = text.strip()

        return text

    def createIssue(self, message, savedata):
        if savedata:
            gisturl = self.createGist('%s/%s save file for with title "%s"'%(self.owner, self.repo, message['title']), None, savedata)
            message['saveurl'] = gisturl

        postdata = {
            'title': message['title'],
            'body': self.formatIssue(message),
        }

        return self._post(self.repourl + '/issues', postdata)['url']
