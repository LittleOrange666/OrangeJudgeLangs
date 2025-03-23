import json

import requests

from tools import download_and_extract


def ask_arch():
    while True:
        print("""please choose your Architecture:
1. x64 (default)
2. riscv64
3. ppc64le
4. arm64""")
        table = {
            "1": "x64",
            "2": "riscv64",
            "3": "ppc64le",
            "4": "arm64"
        }
        arch = input("> ")
        if arch == "":
            return "x64"
        if arch in table:
            return table[arch]
        if arch in table.values():
            return arch
        print("Invalid input")


def main():
    arch = ask_arch()
    print(f"Your architecture is {arch}")
    versions = []
    supported_version = ("8", "11", "17", "21", "16", "18", "19", "20", "22", "23")
    dat = {
        "name": "Java",
        "require_compile": True,
        "source_ext": ".java",
        "exec_name": "{0}.class",
        "compile_cmd": ["/langs/java/{arg}/bin/javac", "{0}"],
        "compile_runner_cmd": ["/langs/java/{arg}/bin/javac", "{0}", "{2}"],
        "exec_cmd": ["/langs/java/{arg}/bin/java", "-classpath", "{folder}", "{1}"],
        "base_name": "BaseJava{idx}",
        "branches": {},
        "default_branch": "Java8",
        "executables": [],
        "seccomp_rule": "golang"
    }
    while True:
        print("Please input the version of Java you want to download:")
        print("Supported versions are:")
        print("8, 11, 17, 21 (LTS), 16, 18, 19, 20, 22, 23")
        if versions:
            print("You can also input '0' to complete the input")
        version = input("> ")
        if version == "0" and versions:
            break
        if version in versions:
            print(f"Version {version} already added")
        elif version in supported_version:
            versions.append(version)
            print(f"Version {version} added")
        else:
            print("Invalid input")
    for version in versions:
        print(f"Downloading Java {version} for {arch}")
        url = f"https://api.github.com/repos/adoptium/temurin{version}-binaries/releases/latest"
        response = requests.get(url)
        data = response.json()
        assets = data["assets"]
        tag_name = data["tag_name"]
        fns = [o["name"] for o in assets]
        fns = [fn for fn in fns if arch in fn and "_linux_" in fn and "jdk" in fn]
        fns = [fn for fn in fns if fn.endswith(".tar.gz")]
        if len(fns) != 1:
            print(f"Error: {len(fns)} files found")
            continue
        fn = fns[0]
        link = f"https://github.com/adoptium/temurin{version}-binaries/releases/download/{tag_name}/{fn}"
        print(f"Downloading from {link}")
        download_and_extract(link, f"langs/java")
        dat["branches"]["Java" + version] = {
            "arg": tag_name,
            "idx": version
        }
        dat["executables"].append(f"/langs/java/{tag_name}/bin/java")
        with open("langs/java/BaseJava" + version + ".java", "w") as f:
            f.write('public class BaseJava'+version+' {\n\tpublic static void main(String[] args) {\n\t}\n}')
    dat["default_branch"] = "Java" + versions[0]
    with open("langs/java.json", "w") as f:
        json.dump(dat, f, indent=4)
    print("Java setup completed")


if __name__ == "__main__":
    main()
