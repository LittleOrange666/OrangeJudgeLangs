import re
from itertools import groupby

import requests

from tools import download_and_extract, ask_arch, choose_versions, save_lang_json, write_base_file

# go must not touch $HOME (the compile user has none) nor the network
GO_ENV = ["/usr/bin/env", "GOCACHE=/tmp/gocache", "GOPATH=/tmp/gopath", "GOTOOLCHAIN=local", "GOPROXY=off",
          "CGO_ENABLED=0"]


def version_key(v: str):
    return tuple(map(int, v[2:].split(".")))


def find_versions(arch_name):
    response = requests.get("https://go.dev/dl/?mode=json&include=all")
    response.raise_for_status()
    files = {}
    reg = re.compile(r"go\d+\.\d+(\.\d+)?$")
    for release in response.json():
        version = release["version"]
        if not release.get("stable") or not reg.match(version):
            continue
        for f in release["files"]:
            if f["os"] == "linux" and f["arch"] == arch_name and f["kind"] == "archive":
                files[version] = f
    return files


def main():
    arch = ask_arch()
    print(f"Your architecture is {arch}")
    arch_name = "amd64" if arch == "x64" else "arm64"
    files = find_versions(arch_name)
    versions = sorted(files, key=version_key, reverse=True)
    # latest patch of each minor version, newest first
    latests = [next(v) for k, v in groupby(versions, lambda x: ".".join(x.split(".")[:2]))][:10]
    mp = {}
    print("Detected versions:")
    for i, a in enumerate(latests):
        print(f"{i + 1}. {a}")
        mp[str(i + 1)] = a
        mp[a] = a
        mp[a[2:]] = a
    chosen = choose_versions(mp)
    dat = {
        "name": "Go",
        "require_compile": True,
        "source_ext": ".go",
        "exec_name": "{0}",
        "compile_cmd": GO_ENV + ["/langs/go/{arg}/go/bin/go", "build", "-o", "{1}", "{0}"],
        "compile_runner_cmd": GO_ENV + ["/langs/go/{arg}/go/bin/go", "build", "-o", "{3}", "{0}", "{2}"],
        "exec_cmd": ["{0}"],
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
        f = files[version]
        link = "https://go.dev/dl/" + f["filename"]
        print(f"Downloading {link}")
        download_and_extract(link, f"langs/go/{version}", f["sha256"])
        name = "Go" + ".".join(version[2:].split(".")[:2])
        dat["branches"][name] = {
            "arg": version
        }
        dat["executables"].append(f"/langs/go/{version}/go/bin/go")
        branch_names.append(name)
    write_base_file("go", "base_go.go", "package main\n\nfunc main() {\n}\n")
    save_lang_json("go", dat, branch_names[0])
    print("Go setup completed")


if __name__ == "__main__":
    main()
