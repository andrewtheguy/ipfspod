#!/usr/bin/env python3

# pip install gitpython

from git import Repo
import os
import sys
import pathlib

PATH_OF_GIT_REPO = './feed_repos/podcastsnew'  # make sure .git folder is properly configured


COMMIT_MESSAGE = 'update contents'

def git_clone():
    print('cloning')
    if not os.path.isdir(PATH_OF_GIT_REPO):
        pathlib.Path(PATH_OF_GIT_REPO).mkdir(parents=True, exist_ok=True)
        Repo.clone_from('git@github.com-andrew:andrewtheguy/podcastsnew.git', PATH_OF_GIT_REPO)


def git_push():

    print('pushing to git')   

    repo = Repo(PATH_OF_GIT_REPO)
    repo.git.add('--all')
    repo.git.commit('-m',COMMIT_MESSAGE)
    origin = repo.remote(name='origin')
    origin.pull()
    origin.push()
 
