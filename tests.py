import os
from repository.utils import GitUtils

def find_pom_files(root_dir):
    pom_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if "pom.xml" in filenames:
            pom_files.append(dirpath)
    return pom_files

repo = "https://github.com/cdefense/vulnerable-java-maven"
# repo = "https://github.com/WebGoat/WebGoat"
repo = "https://github.com/veracode/verademo"
repo = "https://github.com/melix/maven-repository-injection"
GitUtils().clone_public_repo(repo)  
repos = find_pom_files(GitUtils().repo_path)
