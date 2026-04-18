import os
import json
import sqlite3
from packaging.version import Version

DB_FILE = "/Users/sharath/Documents/nodb/db/osv_debian_lite.db"
OSV_DIR = "debian/"  # adjust if needed


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS vulns (
        id TEXT PRIMARY KEY,
        summary TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS packages (
        vuln_id TEXT,
        ecosystem TEXT,
        package TEXT,
        introduced TEXT,
        fixed TEXT
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_pkg ON packages(package);")

    conn.commit()
    conn.close()


def import_osv():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    for root, dirs, files in os.walk(os.path.abspath(OSV_DIR), onerror=print):        
        for file in files:            
            if not file.endswith(".json"):
                continue

            path = os.path.join(root, file)

            try:
                with open(path) as f:
                    data = json.load(f)
            except:
                continue

            vid = data.get("id")
            summary = data.get("summary", "")            
            if not vid:
                continue

            cur.execute("""
            INSERT OR IGNORE INTO vulns (id, summary)
            VALUES (?, ?)
            """, (vid, summary))

            for affected in data.get("affected", []):
                pkg_info = affected.get("package", {})
                pkg = pkg_info.get("name")
                ecosystem = pkg_info.get("ecosystem")

                for r in affected.get("ranges", []):
                    introduced = None
                    fixed = None

                    for e in r.get("events", []):
                        if "introduced" in e:
                            introduced = e["introduced"]
                        if "fixed" in e:
                            fixed = e["fixed"]                    
                    cur.execute("""
                    INSERT INTO packages 
                    (vuln_id, ecosystem, package, introduced, fixed)
                    VALUES (?, ?, ?, ?, ?)
                    """, (vid, ecosystem, pkg, introduced, fixed))

    conn.commit()
    conn.close()
    print("✅ OSV data imported")


def is_vulnerable(version, introduced, fixed):
    try:
        v = Version(version)

        if introduced and introduced != "0":
            if v < Version(introduced):
                return False

        if fixed:
            if v >= Version(fixed):
                return False

        return True
    except:
        return False


def query(package, version):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
    SELECT vuln_id, introduced, fixed 
    FROM packages 
    WHERE package = ?
    """, (package,))

    results = []    
    for vid, intro, fix in cur.fetchall():        
        if is_vulnerable(version, intro, fix):
            results.append((vid,fix))

    conn.close()
    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="OSV-lite scanner")
    parser.add_argument("--init", action="store_true", help="Initialize DB")
    parser.add_argument("--import", dest="do_import", action="store_true", help="Import OSV data")
    parser.add_argument("--pkg", type=str, help="Package name (Maven)")
    parser.add_argument("--ver", type=str, help="Version")

    args = parser.parse_args()

    if args.init:
        init_db()

    elif args.do_import:
        import_osv()

    elif args.pkg and args.ver:
        vulns = query(args.pkg, args.ver)

        if not vulns:
            print("✅ No vulnerabilities found")
        else:
            print(f"⚠️ Found {len(vulns)} vulnerabilities:\n")
            for v in vulns:
                print("-", v)

    else:
        print("Usage:")
        print("  python osv_lite.py --init")
        print("  python osv_lite.py --import")
        print("  python osv_lite.py --pkg group:artifact --ver version")


if __name__ == "__main__":
    main()