from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from maven.utils import MavenUtils
from repository.utils import GitUtils
from db.utils import DBUtils
from db.osv_lite import query
from utils import is_valid_git_url
import os
import asyncio
import aiohttp
# from aiohttp import BasicAuth
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

class Repo(BaseModel):
    url: str

@app.post("/clone")
def clone_repo(repo: Repo):    
    if is_valid_git_url(repo.url):
        status = GitUtils().clone_public_repo(repo.url)    
        return {"status": status}
    else:
        raise HTTPException(status_code=400, detail="Invalid git url")
    
@app.get("/maven/tree")
def get_dependency_tree():
    project_dir = "/tmp/repo"
    tree_path = "/tmp/repo/dependency-tree.txt"
    maven = MavenUtils(project_dir=project_dir)
    if not os.path.exists(tree_path):
        java_version = maven.get_java_version_from_pom()
        maven_version = maven.get_maven_version_from_wrapper()
        docker_image = maven.get_maven_docker_image(maven_version, java_version)    
        maven.run_maven_dependency_tree(docker_image)
    with open(tree_path) as fp:
        tree_text = fp.read()
        dependencies = maven.parse_dependency_tree(tree_text)
    return {"message": dependencies}


# async def find_vulnerability(session, groupID, artifactID, version):

#     auth = BasicAuth(login=os.getenv("SONATYPE_USERNAME"), password=os.getenv("SONATYPE_TOKEN"))
#     SONATYPE_URL = "https://ossindex.sonatype.org/api/v3/component-report"
#     payload = {"coordinates": [f"pkg:maven/{groupID}/{artifactID}@{version}"]}
    

#     async with session.post(SONATYPE_URL, auth=auth, json=payload) as response:
#         return await response.json()


# async def main(dependencies):
#     async with aiohttp.ClientSession() as session:

#         tasks = [
#             find_vulnerability(
#                 session,
#                 dep.get('groupId'),
#                 dep.get('artifactId'),
#                 dep.get("version"),
#             )
#             for dep in dependencies
#         ]

#         results = await asyncio.gather(*tasks)

#         combined_result = []
#         print(results)
#         for result in results:
#             for component in result:
#                 for vul in component.get("vulnerabilities", []):
#                     combined_result.extend(vul.get("id"))            

#         return combined_result

@app.get("/maven/scan")
def get_vuls():
    project_dir = "/tmp/repo"
    tree_path = "/tmp/repo/dependency-tree.txt"
    maven = MavenUtils(project_dir=project_dir)    
    with open(tree_path) as fp:
        tree_text = fp.read()
        dependencies = maven.parse_dependency_tree(tree_text)
    vuls = []
    visited = set()
    for dep in dependencies:
        package = f"{dep.get('groupId')}:{dep.get('artifactId')}"
        version = dep.get('version')
        data = (package,version)
        if data not in visited:
            visited.add(data)
            vul_present = query(package, version)
            if vul_present:
                vuls.extend((package,query(package, version)))
    return {"message": vuls}


# @app.get("/database")
# def get_database():
#     json_files = []
#     folder = "/tmp/advisory-database/advisories/github-reviewed"
#     def find_json(folder):
#         for item in os.listdir(folder):
#             path = os.path.join(folder, item)

#             if os.path.isdir(path):
#                 find_json(path)   # recursion
#             elif item.endswith(".json"):
#                 json_files.append(path)
#     find_json(folder)
#     return json_files
  

@app.get("/")
def read_root():
    return {"message": "Hello, NoDB!"}