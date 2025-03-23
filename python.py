import json
import re
from itertools import groupby

import requests
from bs4 import BeautifulSoup

from tools import download_and_extract, Builder


def find_versions():
    link = "https://www.python.org/ftp/python/"
    response = requests.get(link)
    response.raise_for_status()
    response = response.text
    soup = BeautifulSoup(response, "html.parser")
    versions = []
    reg = re.compile(r"3\.\d+\.\d+/")
    for a in soup.find_all("a"):
        txt = a.text
        if reg.match(txt):
            versions.append(txt[:-1])
    return versions


def main():
    versions = find_versions()
    versions.sort(key=lambda x: tuple(map(int, x.split("."))))
    gps = groupby(versions, lambda x: x.split(".")[0:2])
    print("Detected versions:")
    for i, (k, v) in enumerate(gps):
        l = sorted(map(lambda x:int(x.split(".")[-1]),v))
        print(f"* {k[0]}.{k[1]}.{l[0]}~{l[-1]}")
    while True:
        print("Please input the versions you want to download, separated by comma:")
        inp = input("> ")
        chosen = inp.split(",")
        for x in chosen:
            if x not in versions:
                print("Invalid version: " + x)
                break
        else:
            break
    dat = {
        "name": "Python",
        "require_compile": True,
        "source_ext": ".py",
        "exec_name": "__pycache__/{0}.{ext}.pyc",
        "compile_cmd": ["/langs/python/{arg}/bin/python3", "-m", "py_compile", "{0}"],
        "exec_cmd": ["/langs/python/{arg}/bin/python3", "{0}"],
        "branches": {},
        "executables": []
    }
    with Builder() as builder:
        for x in chosen:
            link = f"https://www.python.org/ftp/python/{x}/Python-{x}.tgz"
            print(f"Downloading {link}")
            download_and_extract(link, f"langs/python")
        print("Compiling...")
        for x in chosen:
            builder.send_cmd(f"cd /langs/python/Python-{x}")
            builder.send_cmd(f"./configure --prefix=/langs/python/python{x} --without-ensurepip")
            builder.send_cmd("make install")
            builder.send_cmd(f"rm -rf /langs/python/Python-{x}")
            arg = f"python{x}"
            v = "".join(x.split(".")[:2])
            dat["branches"]["Python" + x] = {
                "arg": arg,
                "ext": f"cpython-{v}"
            }
            dat["executables"].append(f"/langs/python/{arg}/bin/python3")
    with open("langs/python/base_python.py", "w") as f:
        f.write("\n")
    dat["default_branch"] = "Python" + chosen[0]
    with open("langs/python.json", "w") as f:
        json.dump(dat, f, indent=4)
    print("Python setup completed")


if __name__ == '__main__':
    main()
