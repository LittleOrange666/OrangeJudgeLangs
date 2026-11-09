import platform

import requests

from tools import download_and_extract, save_lang_json

JAVA_FLAGS = [
    "-XX:-UsePerfData",  # do not create /tmp/hsperfdata_*
    "-XX:+UseSerialGC",  # single GC thread, small footprint
    "-Xss64m",  # deep recursion
    # smaller up-front reservations, so the JVM fits in the judge's address space cap (2 * ml + 4GB)
    "-XX:CompressedClassSpaceSize=128m",
    "-XX:ReservedCodeCacheSize=128m",
]


def ask_arch():
    print("Try to detect your architecture")
    plat = platform.machine()
    if plat in ("x86_64", "AMD64"):
        return "x64"
    if plat in ("aarch64", "arm64"):
        return "arm64"
    if plat == "riscv64":
        return "riscv64"
    if plat in ("ppc64", "ppc64le"):
        return "ppc64le"
    print("Unknown architecture detected")
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


def find_versions():
    try:
        response = requests.get("https://api.adoptium.net/v3/info/available_releases")
        response.raise_for_status()
        data = response.json()
        return [str(v) for v in data["available_releases"]], [str(v) for v in data["available_lts_releases"]]
    except (requests.RequestException, KeyError, ValueError):
        return ["8", "11", "17", "21", "25"], ["8", "11", "17", "21", "25"]


def main():
    arch = ask_arch()
    print(f"Your architecture is {arch}")
    versions = []
    supported_version, lts_version = find_versions()
    dat = {
        "name": "Java",
        "require_compile": True,
        "source_ext": ".java",
        "exec_name": "{0}.class",
        "compile_cmd": ["/langs/java/{arg}/bin/javac", "{0}"],
        "compile_runner_cmd": ["/langs/java/{arg}/bin/javac", "{0}", "{2}"],
        "exec_cmd": ["/langs/java/{arg}/bin/java"] + JAVA_FLAGS + ["-classpath", "{folder}", "{1}"],
        "base_name": "BaseJava{idx}",
        "branches": {},
        "executables": [],
        # threads allowed; new processes, other programs, sockets, writing files and signalling others are not
        "seccomp_rule": "runtime",
        # the runtime reserves far more virtual memory than it uses, limit the RSS instead of the address space
        "memory_limit_check_only": True
    }
    while True:
        print("Please input the version of Java you want to download:")
        print("Supported versions are:")
        print(", ".join(v + (" (LTS)" if v in lts_version else "") for v in supported_version))
        if versions:
            print("You can also input '0' to complete the input")
        version = input("> ").strip()
        if version == "0" and versions:
            break
        if version in versions:
            print(f"Version {version} already added")
        elif version in supported_version:
            versions.append(version)
            print(f"Version {version} added")
        else:
            print("Invalid input")
    installed = []
    for version in versions:
        print(f"Downloading Java {version} for {arch}")
        url = f"https://api.github.com/repos/adoptium/temurin{version}-binaries/releases/latest"
        response = requests.get(url)
        if not response.ok:
            print(f"Error: cannot get the release of Java {version} ({response.status_code}), skipped")
            continue
        data = response.json()
        assets = data["assets"]
        tag_name = data["tag_name"]
        fns = [o["name"] for o in assets]
        fns = [fn for fn in fns if arch in fn and "_linux_" in fn and "jdk" in fn]
        fns = [fn for fn in fns if fn.endswith(".tar.gz")]
        if len(fns) != 1:
            print(f"Error: {len(fns)} files found for Java {version}, skipped")
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
        installed.append(version)
        with open("langs/java/BaseJava" + version + ".java", "w") as f:
            f.write('public class BaseJava'+version+' {\n\tpublic static void main(String[] args) {\n\t}\n}')
    if not installed:
        print("No Java version installed")
        return
    save_lang_json("java", dat, "Java" + installed[0])
    print("Java setup completed")


if __name__ == "__main__":
    main()
