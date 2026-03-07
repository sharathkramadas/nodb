class GoUtils:

    def contains_go_build(self, file_path):
        try:
            result = subprocess.run(
                ["strings", file_path],
                capture_output=True,
                text=True,
                errors="ignore"
            )

            content = result.stdout

            if "Go build" in content or "main.main" in content:
                return content

        except Exception:
            pass

        return None

    def export_image(self, image_name, tmp_dir):
        container_id = subprocess.check_output(
            ["docker", "create", image_name],
            text=True
        ).strip()

        tar_path = os.path.join(tmp_dir, "image.tar")

        try:
            subprocess.run(
                ["docker", "export", container_id, "-o", tar_path],
                check=True
            )
        finally:
            subprocess.run(
                ["docker", "rm", container_id],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        extract_path = os.path.join(tmp_dir, "image_fs")
        os.makedirs(extract_path, exist_ok=True)

        subprocess.run(
            ["tar", "-xf", tar_path, "-C", extract_path],
            check=True
        )

        return extract_path

    def find_go_binary(self, image_name, search_string):

        if search_string.startswith("go/"):
            return "Part of go binary"

        elif search_string.startswith("golang.org/") or "." in search_string:

            with tempfile.TemporaryDirectory() as tmp_dir:
                fs_root = self.export_image(image_name, tmp_dir)

                dirs_to_scan = [
                    os.path.join(fs_root, "usr/local/bin"),
                    os.path.join(fs_root, "usr/bin"),
                    os.path.join(fs_root, "bin"),
                ]

                for exe in self.find_executables(dirs_to_scan):

                    content = self.contains_go_build(exe)

                    if content:
                        pattern = re.compile(r"\bgo(\d+(?:\.\d+){0,2})\b")
                        match = pattern.search(content)

                        if match:
                            go_version = match.group(1)

                            if any(search_string in line for line in content.splitlines()):
                                return exe.replace(fs_root, "")
                            else:
                                return "Internal File"

        return False

    def get_tree(self):
        with open("deps.json") as f:
            modules = json.load(f)

        module_dict = {m["Path"]: m for m in modules}
        main_module = next(m for m in modules if m.get("Main"))

        output = subprocess.check_output(["go", "mod", "graph"]).decode().splitlines()

        deps = defaultdict(list)

        for line in output:
            parent, child = line.split()
            deps[parent].append(child)

        def print_tree(node, indent=""):
            print(indent + node)

            for child in deps.get(node, []):
                print_tree(child, indent + "  ")

        print_tree(main_module["Path"])

    def find_vulnerability(self, package_name, package_version, package_ecosystem):

        time.sleep(2)

        url = "https://api.osv.dev/v1/query"

        data = {
            "version": package_version,
            "package": {
                "name": package_name,
                "ecosystem": package_ecosystem
            }
        }

        response = requests.post(url, json=data)

        if response.status_code != 200:
            print(f"Error fetching data : {response.status_code}")
            print(response.json())
            return None

        return [vul.get("id") for vul in response.json().get("vulns", [])]

    def find_non_vulnerable_versions(self, package_name):

        non_vulnerable_versions = []

        url = f"https://proxy.golang.org/{package_name.replace('/', '%2F')}/@v/list"

        response = requests.get(url)

        if response.status_code == 200:
            versions = response.text.splitlines()

            for version in versions:
                vuls_present = self.find_vulnerability(
                    package_name,
                    version,
                    package_ecosystem="Go"
                )

                if not vuls_present:
                    non_vulnerable_versions.append(version)

        return non_vulnerable_versions

    def find_all_versions(self, module):

        url = f"https://proxy.golang.org/{module.replace('/', '%2F')}/@v/list"

        response = requests.get(url)

        if response.status_code == 200:
            versions = response.text.splitlines()

            print(f"Found {len(versions)} versions:")

            for v in versions:
                print(v)

        else:
            print(f"Failed to fetch versions, status code: {response.status_code}")

    def parse_go_version(self, v):

        if not v.startswith("v"):
            raise ValueError(f"Invalid version: {v}")

        base = v.split("-")[0]
        parts = base.lstrip("v").split(".")

        if len(parts) != 3:
            raise ValueError(f"Invalid base version: {v}")

        major, minor, patch = map(int, parts)

        return major, minor, patch

    def version_difference(self, v1, v2):

        major1, minor1, patch1 = self.parse_go_version(v1)
        major2, minor2, patch2 = self.parse_go_version(v2)

        return (
            major2 - major1,
            minor2 - minor1,
            patch2 - patch1,
        )

    def find_go_major_upgrade(self, v1, v2):

        try:
            major_diff, minor_diff, patch_diff = self.version_difference(v1, v2)

            if minor_diff > 5:
                return True
            else:
                return False

        except Exception as e:
            print(e)
            return None
