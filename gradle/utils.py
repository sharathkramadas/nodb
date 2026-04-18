import os 
import re
import sys
import semver
import requests
import docker
from docker.errors import ContainerError, ImageNotFound, APIError
from string import Template
from db.osv_lite import query
from rich.console import Console
from rich.table import Table
from tqdm import tqdm

class GradleUtils:
    def __init__(self, project_dir: str):    
        gradle_files = []
        for dirpath, dirnames, filenames in os.walk(project_dir):
            if "build.gradle" in filenames:
                gradle_files.append(dirpath)
        if len(gradle_files) > 1:
            print("[*] Multi gradle file repos are not supported yet!!!")  
            sys.exit()        
        self.project_dir = gradle_files[0]
        self.gradle_path = os.path.join(self.project_dir, "build.gradle")

        self.dep_tree_file = "dependency-tree.txt"
        self.dep_tree_path = os.path.join(self.project_dir, self.dep_tree_file)

    def compare_versions(self, current, latest):

        try:
            current_sem = semver.VersionInfo.parse(current)
            latest_sem = semver.VersionInfo.parse(latest)

        except ValueError:

            if current != latest:
                return "UPDATE AVAILABLE"
            return "UP-TO-DATE"

        if current_sem.major != latest_sem.major:
            return "MAJOR"

        if current_sem.minor != latest_sem.minor:
            return "MINOR"

        if current_sem.patch != latest_sem.patch:
            return "PATCH"

        return "UP-TO-DATE"

    def get_latest_version(self, group_id, artifact_id):

        url = (
            "https://search.maven.org/solrsearch/select"
            f"?q=g:\"{group_id}\"+AND+a:\"{artifact_id}\"&rows=1&wt=json"
        )

        resp = requests.get(url).json()

        return resp["response"]["docs"][0]["latestVersion"]
    
    def get_java_version_from_gradle(self): 
        self.gradle_path = os.path.join(self.project_dir, "build.gradle") 
        if not os.path.exists(self.gradle_path): 
            return None         
        with open(self.gradle_path, 'r') as f:
            content = f.read()

        patterns = [
            r'sourceCompatibility\s*=\s*[\'"]?(\d+(?:\.\d+)?)[\'"]?',
            r'targetCompatibility\s*=\s*[\'"]?(\d+(?:\.\d+)?)[\'"]?',
            r'JavaVersion\.VERSION_(\d+)',
            r'java\s*\{\s*toolchain\s*\{\s*languageVersion\s*=\s*JavaLanguageVersion\.of\((\d+)\)'
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
            if match:
                return match.group(1)

        return None        

    def get_gradle_version_from_wrapper(self): 
        wrapper_path = os.path.join(self.project_dir, "gradle", "wrapper", "gradle-wrapper.properties") 
        if not os.path.exists(wrapper_path): 
            return "3.8.6" 
        with open(wrapper_path) as f: 
            for line in f: 
                if "distributionUrl" in line: 
                    match = re.search(r'gradle-(\d+(\.\d+)+)-', line) 
                    if match: 
                        return match.group(1) 
                    
    def get_depth(self, indent):        
        indent = indent.replace("|", " ")
        return len(indent) // 5                    
                    
    def clean_dependency(self, dep):        
        dep = re.sub(r"\s+\(.*?\)$", "", dep)

        # Handle version override: a:b:1.0 -> 2.0
        if "->" in dep:
            left, right = dep.split("->")
            dep = left.strip()
            parts = dep.split(":")
            if len(parts) >= 2:
                return parts[0], parts[1], right.strip()

        parts = dep.split(":")
        if len(parts) >= 3:
            return parts[0], parts[1], parts[2]

        return dep, None, None                    

    def parse_dependency_tree(self):
        java_version = self.get_java_version_from_gradle()
        gradle_version = self.get_gradle_version_from_wrapper()
        docker_image = self.get_gradle_docker_image(gradle_version, java_version)    
        self.run_gradle_dependency_tree(docker_image)

        with open(self.dep_tree_path, 'r') as fp:
            tree_text = fp.read()

        dependencies = []
        stack = []

        for line in tree_text.splitlines():

            line = line.strip()

            if not ("+---" in line or "\\---" in line):
                continue

            match = re.match(r"([|\s]*)(\+---|\\---)\s+(.*)", line)
            if not match:
                continue

            indent, _, dep = match.groups()

            depth = self.get_depth(indent)

            group, artifact_id, version = self.clean_dependency(dep)                                

            node = {
                "groupId": group.replace("(",""),
                "artifactId": artifact_id,
                "version": version,                
                "depth": depth,
                "parent": None,
            }

            stack = stack[:depth]

            if depth > 0:
                node["parent"] = stack[-1]["artifactId"]

            stack.append(node)

            dependencies.append(node)

        return dependencies

    def extract_dependencies(self, lines): 
        dependencies = {} 
        pattern = r"^\s*\+-\s*(\S+:\S+):jar:(\S+)" 
        for line in lines: 
            match = re.search(pattern, line) 
            if match: 
                dep = match.group(1) 
                version = match.group(2) 
                dependencies[dep] = ''.join(version.split(":")[:-1]) 
        return dependencies

    def find_highest_parents(self, target_ga):

        deps = self.parse_dependency_tree()

        dep_map = {d["artifactId"]: d for d in deps}

        highest = []

        for d in deps:

            ga = f"{d['groupId']}:{d['artifactId']}"

            if ga != target_ga:
                continue

            current = d

            while current["parent"] is not None:

                parent = current["parent"]

                current = dep_map.get(parent)

                if current is None:
                    break

            if current:

                highest.append(
                    {
                        "root": f"{current['groupId']}:{current['artifactId']}",
                        "version": current["version"],
                    }
                )

        return highest

    def get_gradle_docker_image(self, gradle_version, java_version=None):
        if not gradle_version: 
            gradle_version = "3.9.6"
        if not java_version: 
            java_version = "17" 
        return self.build_docker_image(java_version, gradle_version)

    def build_docker_image(self, java_version="17", gradle_version="3.9.6"):
        name = f"gradle-{gradle_version}-jdk{java_version}"        

        dockerfile_path = "Dockerfile.gradle"
        template_path = os.path.join(os.getcwd(), "gradle", "Dockerfile.template")
        # print(template_path)
        with open(template_path) as f:
            dockerfile_template = Template(f.read())
        variables = {
            "java_version":java_version,
            "gradle_version":gradle_version
        }

        # print(java_version,gradle_version)

        dockerfile_content = dockerfile_template.substitute(variables)

        # print(dockerfile_content)

        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)      
        client = docker.from_env()
        image, logs = client.images.build(
            path=".",                  
            dockerfile=dockerfile_path, 
            tag=name,
            rm=True                     
        )
        print('[*] Docker image built successfully')
        return name

    def fix_vuls(self):
        dependencies = self.parse_dependency_tree()
        visited = set()
        for dep in dependencies:
            package = f"{dep.get('groupId')}:{dep.get('artifactId')}"
            version = dep.get('version')
            data = (package,version)
            if data not in visited:
                visited.add(data)
                vul_present = query(package, version)
                if vul_present:                
                    versions = [v[1] for v in vul_present if v[1]]
                    vuls = [v[0] for v in vul_present if v[0]]
                    if versions:
                        fix_version = max(versions)
                        print(package, vuls, fix_version)

    def run_gradle_dependency_tree(self, docker_image, gradle_path="build.gradle"):
        try:
            client = docker.from_env()

            command = "gradle dependencies --console=plain".split()
            
            container = client.containers.run(
                image=docker_image,
                command=command,
                volumes={self.project_dir: {"bind": "/usr/src/app", "mode": "rw"}},
                working_dir="/usr/src/app",
                remove=True,
                stdout=True,
                stderr=True,
            )
            with open(self.dep_tree_path, "wb") as f:
                f.write(container)
            print("[*] Dependency tree construction succeded") 
        except (ContainerError, ImageNotFound, APIError) as e:
            # print(e)
            print("[*] Dependency tree construction failed") 
            sys.exit()

    def output_table(self):
        console = Console()
        table = Table(title="Vulnerabilities")
        table.add_column("Dependency", style="cyan", no_wrap=True)
        table.add_column("Current version", style="cyan")
        table.add_column("CVE ID", style="cyan")
        table.add_column("Fixed In", style="cyan")    
        dependencies = self.parse_dependency_tree() 
        visited = set()
        printed = set()        
        for dep in dependencies:
            package = f"{dep.get('groupId')}:{dep.get('artifactId')}"
            version = dep.get('version')
            data = (package,version)
            if data not in visited:
                visited.add(data)
                vul_present = query(package, version)
                if vul_present:
                    for v in vul_present:
                        vid, fix_version = v
                        if v not in printed:
                            printed.add((v))
                            table.add_row(package,dep.get('version'), vid, fix_version or "No Fix")                               
        console.print(table)

    def extract_dependencies(self, lines):

        deps = {}

        pattern = r"^\s*\+-\s*(\S+:\S+):jar:(\S+)"

        for line in lines:

            m = re.search(pattern, line)

            if m:

                name = m.group(1)
                version = m.group(2)

                deps[name] = version

        return deps


