import os
from dotenv import load_dotenv
from pathlib import Path
import gitlab
import shutil
from git import Repo
import requests
import yaml

class GitUtils:
    def __init__(self):
        load_dotenv()
        self.PRIVATE_TOKEN = os.getenv("GITLAB_TOKEN")
        self.GITLAB_URL = "https://gitlab.com"
        self.headers = {"PRIVATE-TOKEN": self.PRIVATE_TOKEN}
        self.repo_path = "/tmp/repo"
        self.gl = gitlab.Gitlab(self.GITLAB_URL, private_token=self.PRIVATE_TOKEN)

    def clone_public_repo(self, repo_url):        
        repo = Repo.clone_from(repo_url, self.repo_path)
        return 'Repo clone complete'        

    def clone_repo(self, project_name):
        PROJECT_ID = self.get_project_id(project_name)
        project = self.gl.projects.get(PROJECT_ID)

        folder = Path(self.repo_path)
        if folder.exists() and folder.is_dir():
            shutil.rmtree(folder)

        Repo.clone_from(project.http_url_to_repo, self.repo_path)
        print(f"[+] Cloning {project_name} to {self.repo_path}")

    def get_project_id(self, project) -> int:
        project_encoded = quote(project, safe='')
        url = f"{self.GITLAB_URL}/api/v4/projects/{project_encoded}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()["id"]

    def beautify_yaml(self, file_path):
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)

            with open(file_path, 'w') as f:
                yaml.dump(
                    data,
                    f,
                    sort_keys=False,
                    default_flow_style=False,
                    indent=2
                )

            print(f"[INFO] YAML file '{file_path}' beautified successfully!")

        except Exception as e:
            print(f"[ERROR] Failed to beautify YAML file: {e}")

    def is_maven_repo(self, project_name, ref=None):
        PROJECT_ID = self.get_project_id(project_name)
        project = self.gl.projects.get(PROJECT_ID)
        ref = ref or project.default_branch

        try:
            project.files.get(file_path="pom.xml", ref=ref)
            return True
        except gitlab.exceptions.GitlabGetError:
            return False

    def is_gradle_repo(self, project_name, ref=None):
        PROJECT_ID = self.get_project_id(project_name)
        project = self.gl.projects.get(PROJECT_ID)
        ref = ref or project.default_branch

        try:
            project.files.get(file_path="build.gradle", ref=ref)
            return True
        except gitlab.exceptions.GitlabGetError:
            return False
