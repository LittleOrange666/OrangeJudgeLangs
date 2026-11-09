
import requests

from tools import download_and_extract, ask_arch, choose_versions, save_lang_json, write_base_file

# V8 defaults to a ~1MB stack; the judge allows ml/4 MB of stack (64MB for 256MB), so deep recursion works
NODE_STACK = "--stack-size=65500"


def find_versions(arch_name):
    """Latest release of every Node.js major version that ships a linux tarball for ``arch_name``."""
    response = requests.get("https://nodejs.org/dist/index.json")
    response.raise_for_status()
    latests = {}
    for release in response.json():
        version = release["version"]  # e.g. v22.11.0
        if "-" in version or f"linux-{arch_name}" not in release["files"]:
            continue
        major = int(version[1:].split(".")[0])
        if major < 18:
            continue
        key = tuple(map(int, version[1:].split(".")))
        if major not in latests or key > latests[major][0]:
            latests[major] = (key, version, release["lts"])
    return [(version, lts) for _, version, lts in sorted(latests.values(), reverse=True)]


def get_sha256(version, filename):
    response = requests.get(f"https://nodejs.org/dist/{version}/SHASUMS256.txt")
    response.raise_for_status()
    for line in response.text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == filename:
            return parts[0]
    return None


def install_node(version, arch_name) -> str:
    """Download Node.js ``version`` into langs/javascript, returns the folder name."""
    folder = f"node-{version}-linux-{arch_name}"
    filename = folder + ".tar.xz"
    link = f"https://nodejs.org/dist/{version}/{filename}"
    print(f"Downloading {link}")
    download_and_extract(link, "langs/javascript", get_sha256(version, filename))
    return folder


def main():
    arch = ask_arch()
    print(f"Your architecture is {arch}")
    versions = find_versions(arch)
    mp = {}
    print("Detected versions:")
    for i, (version, lts) in enumerate(versions):
        print(f"{i + 1}. Node.js {version}" + (f" (LTS {lts})" if lts else ""))
        mp[str(i + 1)] = version
        mp[version] = version
        mp[version[1:]] = version
        mp[version[1:].split(".")[0]] = version
    chosen = choose_versions(mp)
    dat = {
        "name": "JavaScript",
        "require_compile": True,
        "source_ext": ".js",
        "exec_name": "{0}.js",
        "compile_cmd": ["/langs/javascript/{arg}/bin/node", "--check", "{0}"],
        "exec_cmd": ["/langs/javascript/{arg}/bin/node", NODE_STACK, "{0}"],
        "branches": {},
        "executables": [],
        # threads allowed; new processes, other programs, sockets, writing files and signalling others are not
        "seccomp_rule": "runtime",
        # the runtime reserves far more virtual memory than it uses, limit the RSS instead of the address space
        "memory_limit_check_only": True
    }
    branch_names = []
    for x in chosen:
        version = mp[x]
        folder = install_node(version, arch)
        name = "NodeJS" + version[1:].split(".")[0]
        dat["branches"][name] = {
            "arg": folder
        }
        dat["executables"].append(f"/langs/javascript/{folder}/bin/node")
        branch_names.append(name)
    write_base_file("javascript", "base_javascript.js", "\n")
    save_lang_json("javascript", dat, branch_names[0])
    print("JavaScript setup completed")


if __name__ == "__main__":
    main()
