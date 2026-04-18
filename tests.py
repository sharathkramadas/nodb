import os
from repository.utils import GitUtils
from gradle.utils import GradleUtils
from maven.utils import MavenUtils
from db.osv_lite import query

# https://github.com/vavkamil/awesome-vulnerable-apps

# Maven tests
repo = "https://github.com/cdefense/vulnerable-java-maven"
repo = "https://github.com/WebGoat/WebGoat"
repo = "https://github.com/veracode/verademo"
repo = "https://github.com/melix/maven-repository-injection"
repo = "https://github.com/OWASP-Benchmark/BenchmarkJava"
repo = "https://github.com/OWASP/SecurityShepherd"
GitUtils().clone_public_repo(repo)  
maven = MavenUtils(project_dir="/tmp/repo")
maven.fix_vuls()


# Gradle tests
repo = "https://github.com/DataDog/vulnerable-java-application.git"
repo = "https://github.com/SasanLabs/VulnerableApp.git"
# GitUtils().clone_public_repo(repo)  
# gradle = GradleUtils(project_dir="/tmp/repo")
# gradle.fix_vuls()


