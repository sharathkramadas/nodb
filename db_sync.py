import os
import json
from rich.console import Console
from rich.table import Table

console = Console()

table = Table(title="Vulnerability DB")

table.add_column("ID", style="magenta", no_wrap=True)
table.add_column("Package", style="cyan")
table.add_column("EcoSystem", style="cyan")
table.add_column("Version", style="cyan")
table.add_column("FixVersion", style="cyan")

json_files = []

def find_json(folder):
    for item in os.listdir(folder):
        path = os.path.join(folder, item)

        if os.path.isdir(path):
            find_json(path)   # recursion
        elif item.endswith(".json"):
            json_files.append(path)

folder = "/tmp/advisory-database/advisories/github-reviewed"
find_json(folder)

for json_file in json_files:
    with open(json_file) as fp:
        data = json.load(fp)
        aliases = data.get('aliases')
        id = aliases[0] if len(aliases) > 0 else data.get('id')
        affected_packages = data.get('affected')
        for package in affected_packages:
            package_name = package.get('package').get('name')
            ecosystem = package.get('package').get('ecosystem')
            ranges = package.get('ranges')
            if ranges: 
                introduced = ranges[0].get('events')[0].get('introduced') 
                if len(ranges[0].get('events')) > 1:
                    event = ranges[0]
                    fixed = event.get('events')[1].get('fixed') or event.get('events')[1].get('last_affected')                                     
                else:
                    fixed =  "NoFix"
            table.add_row(id, package_name, ecosystem, ">="+introduced, fixed)

console.print(table)


