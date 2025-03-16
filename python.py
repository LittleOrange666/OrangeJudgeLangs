import re
from itertools import groupby

import requests
from bs4 import BeautifulSoup


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


if __name__ == '__main__':
    main()
