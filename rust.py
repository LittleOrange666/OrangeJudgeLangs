import platform
import re

import requests
from bs4 import BeautifulSoup

from tools import download_and_extract, Builder, choose_versions, save_lang_json, write_base_file


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
    if plat in ("ppc64", "ppc64le"):
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
            return "x86_64"
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
        mh = reg.match(txt) if txt else None
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
    chosen = choose_versions(mp)
    dat = {
        "name": "Rust",
        "require_compile": True,
        "source_ext": ".rs",
        "exec_name": "{0}",
        "compile_cmd": ["/langs/rust/{arg}/bin/rustc", "-O", "--edition=2021", "{0}", "-o", "{1}"],
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
            workdir = f"/langs/rust/{path}"
            builder.send_cmd_in(f"./install.sh --prefix=/langs/rust/{arg}", workdir)
            builder.send_cmd(f"rm -rf "+workdir)
            dat["branches"]["Rust" + a] = {
                "arg": arg
            }
            dat["executables"].append(f"/langs/rust/{arg}/bin/rustc")
    write_base_file("rust", "base_rust.rs", "fn main() {\n}\n")
    save_lang_json("rust", dat, "Rust" + mp[chosen[0]])
    print("Rust setup completed")


if __name__ == "__main__":
    main()

