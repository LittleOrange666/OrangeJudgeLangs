import json
import re
import tarfile
from io import BytesIO
from itertools import groupby

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


def ask_arch():
    while True:
        print("""please choose your Architecture:
1. x64 (default)
2. arm64""")
        table = {
            "1": "x64",
            "2": "arm64"
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
    link = "https://downloads.python.org/pypy/"
    response = requests.get(link)
    response.raise_for_status()
    response = response.text
    soup = BeautifulSoup(response, "html.parser")
    versions = []
    reg = re.compile(r"pypy(3\.\d+)-(v\d+\.\d+\.\d+)-" + arch_name + ".tar.bz2")
    for a in soup.find_all("a"):
        txt = a.text
        mh = reg.match(txt)
        if mh:
            versions.append(mh.groups())
    return versions


def download_and_extract(link, target):
    response = requests.get(link, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024
    progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)

    file_obj = BytesIO()
    for data in response.iter_content(block_size):
        progress_bar.update(len(data))
        file_obj.write(data)
    progress_bar.close()

    file_obj.seek(0)
    with tarfile.open(fileobj=file_obj, mode="r:*") as tar:
        tar.extractall(path=target)


def main():
    arch = ask_arch()
    print(f"Your architecture is {arch}")
    arch_name = "linux64" if arch == "x64" else "aarch64"
    versions = find_versions(arch_name)
    versions.sort(key=lambda x: tuple(map(int, x[0].split("."))) + tuple(map(int, x[1][1:].split("."))), reverse=True)
    latests = [next(v) for k, v in groupby(versions, lambda x: x[0])]
    print("Detected versions:")
    mp = {}
    for i, (a, b) in enumerate(latests):
        print(f"{i + 1}. python{a} ({b})")
        mp[str(i + 1)] = (a, b)
        mp[a] = (a, b)
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
        "name": "PyPy",
        "require_compile": True,
        "source_ext": ".py",
        "exec_name": "__pycache__/{0}.{ext}.pyc",
        "compile_cmd": ["/langs/pypy/{arg}/bin/pypy3", "-m", "py_compile", "{0}"],
        "exec_cmd": ["/langs/pypy/{arg}/bin/pypy3", "{0}"],
        "branches": {},
        "executables": []
    }
    for x in chosen:
        a, b = mp[x]
        link = f"https://downloads.python.org/pypy/pypy{a}-{b}-{arch_name}.tar.bz2"
        print(f"Downloading {link}")
        download_and_extract(link, f"pypy{a}")
        v = a.replace(".", "")
        arg = f"pypy{a}-{b}-{arch_name}"
        dat["branches"]["PyPy" + a] = {
            "arg": arg,
            "ext": f"pypy{v}"
        }
        dat["executables"].append(f"/langs/pypy/{arg}/bin/pypy3")
    dat["default_branch"] = "PyPy" + mp[chosen[0]][0]
    with open("langs/pypy.json", "w") as f:
        json.dump(dat, f, indent=4)
    print("PyPy setup completed")


if __name__ == '__main__':
    main()
