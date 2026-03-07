import os
import re
import time
import json
import glob
import socket
import shutil
import subprocess
import requests
import ipaddress
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote_plus, quote, urlparse
from collections import defaultdict
from typing import Dict

import semver
from lxml import etree

from string import Template


class MavenUtils:

    NS = {"m": "http://maven.apache.org/POM/4.0.0"}

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.pom_path = os.path.join(project_dir, "pom.xml")

        self.dep_tree_file = "dependency-tree.txt"
        self.dep_tree_path = os.path.join(project_dir, self.dep_tree_file)

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

    def check_java_requirement(self, group_id, artifact_id, version):

        try:

            base = "https://repo1.maven.org/maven2"

            path = f"{group_id.replace('.','/')}/{artifact_id}/{version}/{artifact_id}-{version}.pom"

            url = f"{base}/{path}"

            resp = requests.get(url)

            if resp.status_code != 200:
                return None

            root = ET.fromstring(resp.text)

            props = root.find("m:properties", self.NS)

            if props is not None:

                java_version = props.find("m:maven.compiler.source", self.NS)

                if java_version is not None:
                    return java_version.text

            return None

        except Exception:
            return None

    def parse_dependency_tree(self, tree_text):

        dependencies = []
        stack = []

        for line in tree_text.splitlines():

            line = line.strip()

            if not line:
                continue

            line = re.sub(r"^\[INFO\]\s*", "", line)

            match = re.match(r"((\| | )*)(\+-|\\-)\s*(.*)", line)

            if not match:
                continue

            indent, _, _, artifact = match.groups()

            depth = len(indent) // 3

            parts = artifact.split(":")

            if len(parts) < 5:
                continue

            group, artifact_id, packaging, version, scope = parts[:5]

            node = {
                "groupId": group.replace("(",""),
                "artifactId": artifact_id,
                "version": version,
                "scope": scope.split(" ")[0].strip(),
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

    def find_highest_parents(self, tree_text, target_ga):

        deps = self.parse_dependency_tree(tree_text)

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

    def find_vulnerability(self, package_name, version):

        url = "https://api.osv.dev/v1/query"

        data = {
            "version": version,
            "package": {"name": package_name},
        }

        r = requests.post(url, json=data)

        if r.status_code != 200:
            return []

        vulns = r.json().get("vulns", [])

        return [v["id"] for v in vulns]

    def load_pom(self):

        parser = etree.XMLParser(remove_blank_text=False)

        return etree.parse(self.pom_path, parser)

    def save_pom(self, tree):

        tree.write(
            self.pom_path,
            encoding="UTF-8",
            xml_declaration=True,
        )

    def find_dependency(self, root, group_id, artifact_id):

        for dep in root.findall(".//m:dependency", self.NS):

            gid = dep.findtext("m:groupId", namespaces=self.NS)

            aid = dep.findtext("m:artifactId", namespaces=self.NS)

            if gid == group_id and aid == artifact_id:
                return dep

        return None

    def update_dependency_version(self, root, dep, new_version):

        version = dep.find("m:version", self.NS)

        if version is None:

            version = etree.SubElement(
                dep,
                "{%s}version" % self.NS["m"],
            )

        version.text = new_version

    def inject_dependency(self, root, group_id, artifact_id, version):

        deps = root.find("m:dependencies", self.NS)

        if deps is None:

            deps = etree.SubElement(
                root,
                "{%s}dependencies" % self.NS["m"],
            )

        dep = etree.SubElement(
            deps,
            "{%s}dependency" % self.NS["m"],
        )

        etree.SubElement(dep, "{%s}groupId" % self.NS["m"]).text = group_id
        etree.SubElement(dep, "{%s}artifactId" % self.NS["m"]).text = artifact_id
        etree.SubElement(dep, "{%s}version" % self.NS["m"]).text = version

    def get_java_version_from_pom(self): 
        pom_path = os.path.join(self.project_dir, "pom.xml") 
        if not os.path.exists(pom_path): 
            return None 
        tree = ET.parse(pom_path) 
        root = tree.getroot() 
        ns = {"m": root.tag.split("}")[0].strip("{")} 
        props = root.find("m:properties", ns) 
        if props is not None: 
            for tag in ["java.version", "maven.compiler.source", "maven.compiler.target"]: 
                el = props.find(f"m:{tag}", ns) 
                if el is not None and el.text: 
                    return el.text.strip() 
        for plugin in root.findall(".//m:plugin", ns): 
            artifact = plugin.find("m:artifactId", ns) 
            if artifact is not None and artifact.text == "maven-compiler-plugin": 
                source = plugin.find(".//m:source", ns) 
                target = plugin.find(".//m:target", ns) 
                if source is not None: 
                    return source.text.strip() 
                if target is not None: 
                    return target.text.strip() 
        return None

    def get_maven_version_from_wrapper(self): 
        wrapper_path = os.path.join(self.project_dir, ".mvn", "wrapper", "maven-wrapper.properties") 
        if not os.path.exists(wrapper_path): 
            return "3.8.6" 
        with open(wrapper_path) as f: 
            for line in f: 
                if "distributionUrl" in line: 
                    match = re.search(r'apache-maven-([\d.]+)-bin\.zip', line) 
                    if match: 
                        if match.group(1) == "3.6.0": 
                            return "3.8.1"# safe default 

    def get_maven_docker_image(self, maven_version, java_version=None):
        if not maven_version: 
            maven_version = "3.9.6"
        if not java_version: 
            java_version = "17" 
        return self.build_docker_image(java_version, maven_version)

    def build_docker_image(self, java_version="17", maven_version="3.9.6"):

        name = f"mvn-{maven_version}-jdk{java_version}"        

        dockerfile_path = "Dockerfile.maven"
        template_path = os.path.join(os.getcwd(), "maven", "Dockerfile.template")
        with open(template_path) as f:
            dockerfile_template = Template(f.read())
        variables = {
            "java_version":java_version,
            "maven_version":maven_version
        }

        dockerfile_content = dockerfile_template.substitute(variables)

        print(dockerfile_content)
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        subprocess.run(
            [
                "docker",
                "build",
                "-t",
                name,
                "-f",
                dockerfile_path,
                ".",
            ],
            check=True,
        )

        return name

    def run_maven_dependency_tree(self, docker_image):
        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{self.project_dir}:/usr/src/app",
            "-w",
            "/usr/src/app",
            docker_image,
            "mvn",
            "dependency:tree",
            "-Dscope=runtime",
            "-DoutputType=text",
            "-Dverbose",
            f"-DoutputFile={self.dep_tree_file}",
        ]

        subprocess.run(cmd)

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

    def scan_dependencies(self):

        with open(self.dep_tree_path) as f:

            lines = f.readlines()

        deps = self.extract_dependencies(lines)

        for pkg, version in deps.items():

            group, artifact = pkg.split(":")

            print(f"\nScanning {pkg}:{version}")

            vulns = self.find_vulnerability(pkg, version)

            if vulns:

                print("Vulnerabilities:", vulns)

                latest = self.get_latest_version(group, artifact)

                print("Latest:", latest)

                print(
                    "Version diff:",
                    self.compare_versions(version, latest),
                )

