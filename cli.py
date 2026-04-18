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

def main():

    parser = argparse.ArgumentParser(description="Scan & Fix")
    parser.add_argument("--scan", help="Git URL to scan")
    parser.add_argument("--fix", help="Git URL to fix")

    args = parser.parse_args()

    project_dir = "/tmp/repo"
    tree_path = "/tmp/repo/dependency-tree.txt"

    if args.scan:
        if is_valid_git_url(args.scan):
            status = GitUtils().clone_public_repo(args.scan)  
            maven = MavenUtils(project_dir=project_dir) 
            maven.output_table()              
    elif args.fix:
        if is_valid_git_url(args.scan):
            status = GitUtils().clone_public_repo(args.fix)
            maven = MavenUtils(project_dir=project_dir)   
            maven.fix_vuls()
    else:
        print("Usage:")
        print("  python cli.py --scan")
        print("  python cli.py --fix")


if __name__ == "__main__":
    main()