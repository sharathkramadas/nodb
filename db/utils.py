class DBUtils:

    def __init__(self):
        load_dotenv()
        self.sonatype_username = os.getenv("SONATYPE_USERNAME")
        self.sonatype_token = os.getenv("SONATYPE_TOKEN")
        self.vulnerablecode_token = os.getenv("VULNERABLECODE_TOKEN")

    def find_fix_version(self, groupID, artifactID, version):
        time.sleep(1)

        purl = f"pkg:maven/{groupID}/{artifactID}@{version}"
        url = f"http://public.vulnerablecode.io/api/v2/packages/?purl={purl}"

        r = requests.get(url)
        r.raise_for_status()

        results = r.json().get("results")
        if not results or not results.get("packages"):
            return None

        return results["packages"][0].get("next_non_vulnerable_version")

    def python_db(self, package_name, package_version):
        time.sleep(1)

        PYPI_DB_URL = f"https://pypi.org/pypi/{package_name}/{package_version}/json"
        r = requests.get(PYPI_DB_URL)
        r.raise_for_status()

        return r.json().get("vulnerabilities", [])

    def java_db(self, groupID, artifactID, version):
        time.sleep(1)

        auth = (self.sonatype_username, self.sonatype_token)
        SONATYPE_URL = "https://ossindex.sonatype.org/api/v3/component-report"
        data = {"coordinates": [f"pkg:maven/{groupID}/{artifactID}@{version}"]}

        r = requests.post(SONATYPE_URL, auth=auth, json=data)
        r.raise_for_status()

        vuls = []
        for component in r.json():
            for vul in component.get("vulnerabilities", []):
                vuls.append(vul.get("id"))

        return vuls

    def get_nvd_cve_info(self, cve_id):
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"

        response = requests.get(url)
        response.raise_for_status()

        return response.json()
