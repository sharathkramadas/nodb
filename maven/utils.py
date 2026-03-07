import requests
import docker
import os
import subprocess
import sys
import tempfile
import shutil
import re
import json
from collections import defaultdict
import boto3
import time
import yaml
import requests
from urllib.parse import quote_plus, quote
from pathlib import Path
import xml.etree.ElementTree as ET
import semver
import time
from lxml import etree
import gitlab
from dotenv import load_dotenv
from git import Repo
import json
import os
import asyncio
import requests
from typing import Dict
import ipaddress
from urllib.parse import urlparse
import socket 
import glob
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from playwright.async_api import async_playwright


class MavenUtils:
    def __init__(self, project_dir):
        self.NS = {"m": "http://maven.apache.org/POM/4.0.0"}
        self.project_dir = project_dir
        self.pom_path = os.path.join(self.project_dir, "pom.xml")
        self.dep_tree_file_name = "dependency-tree.txt"
        self.dep_tree_path = os.path.join(self.project_dir, self.dep_tree_file_name)

  def compare_versions(self, current, latest):
        try:
            current_sem = semver.VersionInfo.parse(current)
            latest_sem = semver.VersionInfo.parse(latest)
        except ValueError:
            if current != latest:
                return "UPDATE AVAILABLE"
            else:
                return "UP-TO-DATE"
        if current_sem.major != latest_sem.major:
            return 'MAJOR'
        elif current_sem.minor != latest_sem.minor:
            return 'MINOR'
        elif current_sem.patch != latest_sem.patch:
            return 'PATCH'
        else:
            return 'UP-TO-DATE'

    
