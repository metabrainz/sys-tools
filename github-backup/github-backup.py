#!/usr/bin/env python
#
# Simple github backup
#
# Given a user name, find a list of repos for that user and then clone --mirror
# them if they do not exist. If they do exist, do a git fetch -all on them.
# This gives us a backup of the repo in case something happens to github.
#

import sys
import os
import urllib2
import json;
from subprocess import call

def get_repo_list(user):
    """ Fetch a list of public repos for a given user."""

    url = "https://api.github.com/users/%s/repos" % user
    while True:
        try:
            opener = urllib2.build_opener()
            f = opener.open(url)
        except urllib2.URLError, e:
            if e.code == 403:
                sys.stdout.write("Requesting data too fast! Sleeping!\n")
                sleep(5)
                continue
            return (None, e)

        data = json.loads(f.read())
        f.close();
        return (data, "")

def clone_repo(repo, dir):
    """Given a repo JSON structure and a directory, clone --mirror the repo into that dir """
    try:
        os.makedirs(dir)
    except OSError, e:
        print "Cannot create repo backup dir: %s" % e
        return False

    os.chdir(dir)
    return call(["git", "clone", "--mirror", repo["clone_url"]])     

def update_repo(repo, dir):
    '''Update an existing repo by doing a git fetch -all'''
    os.chdir(dir)
    return call(["git", "fetch", "--all"])     

if len(sys.argv) < 3:
    print "Usage: %s <github user name> <backup dir>" % sys.argv[0]
    sys.exit(-1)

user = sys.argv[1]
dir = sys.argv[2]

dir = os.path.abspath(dir)

repos, err = get_repo_list(user)
if err:
    print "error fetching repo list: %s" % err
    sys.exit(-1)

if not os.path.exists(dir):
    try:
        os.makedirs(dir)
    except OSError, e:
        print "Cannot create backup dir: %s" % e
        sys.exit(-1)

for repo in repos:
    print "%s: %s" % (repo['name'], repo['clone_url'])
    repo_dir = os.path.join(dir, repo['name'])
    if not os.path.exists(repo_dir):
        clone_repo(repo, repo_dir)
    else:
        update_repo(repo, repo_dir)
    print

sys.exit(0)
