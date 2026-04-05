import os
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

table.add_column("ID", style="magenta", no_wrap=True)
table.add_column("Package", style="cyan")
table.add_column("EcoSystem", style="cyan")
table.add_column("Version", style="cyan")
table.add_column("FixVersion", style="cyan")

def main():

    parser = argparse.ArgumentParser(description="Vul scanner")
    parser.add_argument("--scan", help="Git URL to scan")

    args = parser.parse_args()

    if args.scan:
        if is_valid_git_url(args.scan):
            tree_path = "/tmp/repo/dependency-tree.txt"
            project_dir = "/tmp/repo"
            maven = MavenUtils(project_dir=project_dir)
            if not os.path.exists(tree_path):
                status = GitUtils().clone_public_repo(args.scan)  
                java_version = maven.get_java_version_from_pom()
                maven_version = maven.get_maven_version_from_wrapper()
                docker_image = maven.get_maven_docker_image(maven_version, java_version)    
                maven.run_maven_dependency_tree(docker_image)
            with open(tree_path) as fp:
                tree_text = fp.read()
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
                                    table.add_row(vid, package, "Maven", dep.get('version'), fix_version or "No Fix")   
                console.print(table)
    
    else:
        print("Usage:")
        print("  python cli.py --scan")


if __name__ == "__main__":
    main()