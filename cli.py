import os
import sys
import json
import sqlite3
from packaging.version import Version
import argparse
from maven.utils import MavenUtils
from repository.utils import GitUtils
from utils import is_valid_git_url
from db.osv_lite import query
from rich.console import Console
from rich.table import Table

console = Console()

table = Table(title="Vulnerabilities")
table.add_column("Dependency", style="cyan", no_wrap=True)
table.add_column("Current version", style="cyan")
table.add_column("CVE ID", style="cyan")
table.add_column("Fixed In", style="cyan")
# table.add_column("Recommended Upgrade", style="cyan")
# table.add_column("FixVersion", style="cyan")

def main():

    parser = argparse.ArgumentParser(description="Scan & Fix")
    parser.add_argument("--scan", help="Git URL to scan")
    parser.add_argument("--fix", help="Git URL to fix")

    args = parser.parse_args()

    project_dir = "/tmp/repo"
    tree_path = "/tmp/repo/dependency-tree.txt"

    if args.scan:
        if is_valid_git_url(args.scan):
            if not os.path.exists(tree_path):
                status = GitUtils().clone_public_repo(args.scan)  
                maven = MavenUtils(project_dir=project_dir)
                java_version = maven.get_java_version_from_pom()
                maven_version = maven.get_maven_version_from_wrapper()
                docker_image = maven.get_maven_docker_image(maven_version, java_version)    
                maven.run_maven_dependency_tree(docker_image)
            tree_path = os.path.join(maven.project_dir, "dependency-tree.txt")
            with open(tree_path) as fp:
                tree_text = fp.read()
                maven = MavenUtils(project_dir=project_dir)
                dependencies = maven.parse_dependency_tree(tree_text) 
                visited = set()
                printed = set()
                vuls = []
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
                                    # table.add_row(package,vid, package, "Maven", dep.get('version'), fix_version or "No Fix")   
                console.print(table)
    elif args.fix:
        status = GitUtils().clone_public_repo(args.fix)
        maven = MavenUtils(project_dir=project_dir)
        java_version = maven.get_java_version_from_pom()
        maven_version = maven.get_maven_version_from_wrapper()
        docker_image = maven.get_maven_docker_image(maven_version, java_version)    
        maven.run_maven_dependency_tree(docker_image)
        tree_path = os.path.join(maven.project_dir, "dependency-tree.txt")
        if not os.path.exists(tree_path):
            sys.exit()
        else:
            with open(tree_path) as fp:
                tree_text = fp.read()
                dependencies = maven.parse_dependency_tree(tree_text) 
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
                            if versions:
                                fix_version = max(versions)
                                maven.pom_update(package,fix_version)
                            # for v in vul_present:
                            #     vid, fix_version = v
                            #     if fix_version:
                            #         pass
    else:
        print("Usage:")
        print("  python cli.py --scan")
        print("  python cli.py --fix")


if __name__ == "__main__":
    main()