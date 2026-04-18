import os
import tarfile
import subprocess
import docker
import json
from utils import OSUtils
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db.osv_debian_lite import query

client = docker.from_env()

def save_image(image_name, output_tar="image.tar"):    
    output_file = "image.tar"

    image = client.images.get(image_name)

    with open(output_file, "wb") as f:
        for chunk in image.save(named=True):
            f.write(chunk)

    print(f"Image saved to {output_file}")    

def extract_image(tar_path="image.tar", extract_dir="image"):
    with tarfile.open(tar_path) as tar:
        tar.extractall(path=extract_dir)

def safe_extract(tar, path):
    for member in tar.getmembers():
        # Skip device files (block/char)
        if member.ischr() or member.isblk():
            continue

        # Optional: skip FIFOs too
        if member.isfifo():
            continue

        try:
            tar.extract(member, path=path)
        except PermissionError:
            # Skip anything else that fails
            continue

def build_rootfs(image_dir="image", rootfs_dir="rootfs"):
    os.makedirs(rootfs_dir, exist_ok=True)

    manifest_path = os.path.join(image_dir, "manifest.json")

    with open(manifest_path) as f:
        manifest = json.load(f)        

    layers = manifest[0]["Layers"]

    for layer_file in layers:
        layer_path = os.path.join(image_dir, layer_file)

        print(f"[+] Applying layer: {layer_file}")

        with tarfile.open(layer_path) as layer:
            # layer.extractall(path=rootfs_dir)
            safe_extract(layer, rootfs_dir)

def get_rpm_packages(image_name):
    command = [        
        "rpm", "-qa", "--queryformat", "%{NAME} %{VERSION}\\n"
    ]
            
    container = client.containers.run(
        image=image_name,
        command=command,
        remove=True,
        stdout=True,
        stderr=True,
    )

    packages = []
    for line in container.splitlines():
        parts = line.split()
        if len(parts) == 2:
            packages.append({
                "name": parts[0].decode(),
                "version": parts[1].decode()
            })

    return packages                    

def get_debain_packages(image_name):
    packages = []

    command = [        
        "dpkg-query", "-f", "${binary:Package} ${Version}\n", "-W"
    ]
            
    container = client.containers.run(
        image=image_name,
        command=command,
        remove=True,
        stdout=True,
        stderr=True,
    )

    packages = []
    for line in container.splitlines():
        parts = line.split()
        if len(parts) == 2:
            packages.append({
                "name": parts[0].decode(),
                "version": parts[1].decode()
            })

    return packages

def detect_os(image_name):
    data = OSUtils().find_os(image_name)

    os_id = data.get("ID", "").lower()

    if os_id in ["ubuntu", "debian"]:
        return "debian"
    elif os_id in ["amzn", "amazon"]:
        return "amazon"
    elif os_id in ["alpine"]:
        return "alpine"
    elif os_id in ["rhel"]:
        return "redhat"
    else:
        return os_id    

def scan(image_name):
    os_id = detect_os(image_name)
    if os_id == "amazon":
        packages = get_rpm_packages(image_name)        
    elif os_id == "debian":
        packages = get_debain_packages(image_name)
        for package in packages:            
            vuls = query(package.get('name'), package.get('version'))
            if vuls:
                print(package.get('name'), vuls)        

image_name = "gradle-8.5-jdk17:latest"
image_name = "postgres:15"
scan(image_name)                    