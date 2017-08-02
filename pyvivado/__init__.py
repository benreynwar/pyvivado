import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def get_git_label():
    wd = os.getcwd()
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    git_label = subprocess.check_output(['git', 'describe', '--always'])
    git_label = git_label.decode('ascii')[:-1]
    os.chdir(wd)
    return git_label
