#!/usr/bin/env python3

# pip install gitpython

from git import Repo
import sys

PATH_OF_GIT_REPO = '../podcastsnew'  # make sure .git folder is properly configured
COMMIT_MESSAGE = 'update contents'

def git_push(filename):
    print('pushing to git')   

    repo = Repo(PATH_OF_GIT_REPO)
    repo.index.add(filename)
    repo.index.commit(COMMIT_MESSAGE)
    origin = repo.remote(name='origin')
    origin.pull()
    origin.push()
 
