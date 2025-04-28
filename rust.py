import json
import platform
import re

import requests
from bs4 import BeautifulSoup

from tools import download_and_extract, Builder


def ask_arch():
    print("Try to detect your architecture")
    plat = platform.machine()
    if plat in ("x86_64", "AMD64"):
        return "x86_64"
    if plat == "i686":
        return "i686"
    if plat in ("aarch64", "arm64"):
        return "aarch64"
    if plat == "riscv64":
        return "riscv64gc"
    if plat == "ppc64":
        return "powerpc64"
    print("Unknown architecture detected")
    while True:
        print("""please choose your Architecture:
1. x86_64 (default)
2. aarch64
3. riscv64gc
4. i686
5. loongarch64
6. powerpc64""")
        table = {
            "1": "x86_64",
            "2": "aarch64",
            "3": "riscv64gc",
            "4": "i686",
            "5": "loongarch64",
            "6": "powerpc64"
        }
        arch = input("> ")
        if arch == "":
            return "x64"
        if arch in table:
            return table[arch]
        if arch in table.values():
            return arch
        print("Invalid input")


def find_versions(arch_name):
    link = "https://forge.rust-lang.org/infra/archive-stable-version-installers.html"
    response = requests.get(link)
    response.raise_for_status()
    response = response.text
    soup = BeautifulSoup(response, "html.parser")
    versions = []
    reg = re.compile(r"https://static.rust-lang.org/dist/rust-(\d+\.\d+\.\d+)-"+arch_name+"-unknown-linux-gnu.tar.gz")
    for a in soup.find_all("a"):
        txt = a.get("href")
        mh = reg.match(txt)
        if mh:
            versions.append(mh.groups()[0])
    versions = list(set(versions))
    return versions


def main():
    arch = ask_arch()
    print(f"Your architecture is {arch}")
    versions = find_versions(arch)
    versions.sort(key=lambda x: tuple(map(int, x.split("."))), reverse=True)
    mp = {}
    for i, a in enumerate(versions):
        print(f"{i + 1}. rust-{a}")
        mp[str(i + 1)] = a
        mp[a] = a
    while True:
        print("Please input the versions you want to download, separated by comma:")
        inp = input("> ")
        chosen = inp.split(",")
        for x in chosen:
            if x not in mp:
                print("Invalid version: " + x)
                break
        else:
            break
    dat = {
        "name": "Rust",
        "require_compile": True,
        "source_ext": ".rs",
        "exec_name": "{0}",
        "compile_cmd": ["/langs/rust/{arg}/bin/rustc", "{0}"],
        "exec_cmd": ["{0}"],
        "branches": {},
        "executables": [],
        "seccomp_rule": "none"
    }
    with Builder() as builder:
        for x in chosen:
            a = mp[x]
            link = f"https://static.rust-lang.org/dist/rust-{a}-{arch}-unknown-linux-gnu.tar.gz"
            print(f"Downloading {link}")
            download_and_extract(link, f"langs/rust")
        print("Installing...")
        for x in chosen:
            a = mp[x]
            arg = f"rust-{a}"
            path = f"rust-{a}-{arch}-unknown-linux-gnu"
            builder.send_cmd(f"cd /langs/rust/{path}")
            builder.send_cmd(f"./install.sh --prefix=/langs/rust/{arg}")
            builder.send_cmd(f"rm -rf /langs/rust/{path}")
            dat["branches"]["Rust" + a] = {
                "arg": arg
            }
            dat["executables"].append(f"/langs/rust/{arg}/bin/rustc")
    with open("langs/rust/base_rust.rs", "w") as f:
        f.write("fn main(){\n}\n")
    dat["default_branch"] = "Rust" + chosen[0]
    with open("langs/rust.json", "w") as f:
        json.dump(dat, f, indent=4)
    print("Rust setup completed")


if __name__ == "__main__":
    main()

