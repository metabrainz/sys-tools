#!/usr/bin/env python
#
# Simple github backup
#
# Given a user name, find a list of repos for that user and then clone --mirror
# them if they do not exist. If they do exist, do a git fetch -all on them.
# This gives us a backup of the repo in case something happens to github.
#

from subprocess import check_output
import argparse
import json
import logging
import os
import sys
import urllib2

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

def clone_repo(clone_url, dir):
    """Given a repo JSON structure and a directory, clone --mirror the repo into that dir """
    try:
        os.makedirs(dir)
    except OSError, e:
        log.error("Cannot create repo backup dir: %s" % e)
        return False

    logging.debug("Calling git clone --mirror %s %s" % (clone_url, dir))
    try:
        check_output(["git", "clone", "--mirror", clone_url, dir])
        return True
    except subprocess.CalledProccessError, e:
        loging.error("Failed to clone: %s" % e.output)

def update_repo(repo, dir):
    """Update an existing repo"""
    logging.debug("Calling git remote update")
    try:
        os.chdir(dir)
        check_output(["git", "remote", "update"])
    except subprocess.CalledProcessError, e:
        logging.error("Failed to update: %s" % e.output)

logging.basicConfig(level=logging.INFO)
parser = argparse.ArgumentParser(description='Backup all repositories for a given GitHub user.')
parser.add_argument('user', help='Backup all repositories owned by this username')
parser.add_argument('dir', help='The directory to create backups in')

args = parser.parse_args()
dir = os.path.abspath(args.dir)

repos, err = get_repo_list(args.user)
if err:
    logging.critical("error fetching repo list: %s" % err)
    sys.exit(-1)

if not os.path.exists(dir):
    try:
        os.makedirs(dir)
    except OSError, e:
        logging.critical("Cannot create backup dir: %s" % e)
        sys.exit(-1)

for repo in repos:
    logging.info("Backing up %s (%s)" % (repo['name'], repo['clone_url']))
    repo_dir = os.path.join(dir, repo['name'])
    if not os.path.exists(repo_dir):
        clone_repo(repo, repo_dir)
    else:
        update_repo(repo, repo_dir)

sys.exit(0)
