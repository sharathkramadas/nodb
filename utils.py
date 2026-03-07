import git

def is_valid_git_url(url):
    try:
        git.cmd.Git().ls_remote(url)
        return True
    except git.exc.GitCommandError:
        return False
