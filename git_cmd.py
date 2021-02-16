#!/usr/bin/env python3

# pip install gitpython

from git import Repo
import sys

PATH_OF_GIT_REPO = '../podcastsnew'  # make sure .git folder is properly configured
COMMIT_MESSAGE = 'update contents'

def git_push():
    print('pushing to git')   
    try:
        repo = Repo(PATH_OF_GIT_REPO)
        repo.index.add('latest_feed.xml')
        repo.index.commit(COMMIT_MESSAGE)
        origin = repo.remote(name='origin')
        origin.pull()
        origin.push()
    except:
        print('Some error occured while pushing the code',file=sys.stderr)    
