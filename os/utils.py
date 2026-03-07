class OSUtils:

    def __init__(self):
        pass

    def parse_os_release(self, text):
        data = {}

        for line in text.splitlines():
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            value = value.strip().strip('"')
            data[key] = value

        return data

    def find_os(self, image):
        client = docker.from_env()

        output = client.containers.run(
            image=image,
            command="cat /etc/os-release",
            entrypoint="",
            remove=True,
        )

        return self.parse_os_release(output.decode())

    def is_executable(self, file_path):
        return os.path.isfile(file_path) and os.access(file_path, os.X_OK)

    def find_executables(self, dirs):
        for dir_path in dirs:
            if not os.path.exists(dir_path):
                continue

            for root, _, files in os.walk(dir_path):
                for name in files:
                    file_path = os.path.join(root, name)
                    if self.is_executable(file_path):
                        yield file_path
                      
class AlpineUtils(OSUtils):

    def load_alpine_secdb(self, branch):
        SECDB_URL_TEMPLATE = "https://secdb.alpinelinux.org/v{branch}/main.json"
        url = SECDB_URL_TEMPLATE.format(branch=branch)

        resp = requests.get(url, timeout=15)
        resp.raise_for_status()

        return resp.json()

    def find_alpine_package(self, distroversion, package_name, package_version):
        reponame = "main"
        urlprefix = "https://dl-cdn.alpinelinux.org/alpine"
        major_minor = ".".join(distroversion.split(".")[:2])
        arch = "aarch64"

        url = f"{urlprefix}/v{major_minor}/{reponame}/{arch}/{package_name}-{package_version}.apk"

        resp = requests.get(url, timeout=15)
        return resp.status_code == 200
