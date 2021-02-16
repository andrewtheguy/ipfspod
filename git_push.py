#!/usr/bin/env python3

# pip install gitpython

from git import Repo

PATH_OF_GIT_REPO = '../podcastsnew/.git'  # make sure .git folder is properly configured
COMMIT_MESSAGE = 'update contents'

def git_push():
    try:
        repo = Repo(PATH_OF_GIT_REPO)
        repo.git.add(update=True)
        repo.index.commit(COMMIT_MESSAGE)
        origin = repo.remote(name='origin')
        origin.push()
    except:
        print('Some error occured while pushing the code')    

git_push()