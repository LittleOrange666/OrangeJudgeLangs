import json
import os
import shutil
from itertools import groupby

import requests

from javascript import find_versions as find_node_versions, install_node, NODE_STACK
from tools import download_and_extract, ask_arch, choose_versions, save_lang_json, write_base_file

REGISTRY = "https://registry.npmjs.org/"

# tsc prints its diagnostics to stdout, OrangeJudge only reports stderr as compile error -> redirect
TSC_FLAGS = ("--pretty false --target es2022 --module nodenext --strict false --skipLibCheck "
             "--types node --typeRoots /langs/typescript/{arg}/node_modules/@types")


def parse_version(v: str):
    return tuple(map(int, v.split(".")))


def stable_versions(meta) -> list[str]:
    return sorted((v for v in meta["versions"] if "-" not in v), key=parse_version, reverse=True)


def resolve_range(name: str, spec: str) -> dict:
    """Resolve a simple npm version range (exact, ~x.y.z, ^x.y.z) to the newest matching version's metadata."""
    response = requests.get(REGISTRY + name)
    response.raise_for_status()
    meta = response.json()
    if spec[0] in "~^":
        base = parse_version(spec[1:])
        n = 2 if spec[0] == "~" else 1
        candidates = [v for v in stable_versions(meta)
                      if parse_version(v)[:n] == base[:n] and parse_version(v) >= base]
    else:
        candidates = [spec]
    if not candidates:
        raise ValueError(f"No version of {name} matches {spec}")
    return meta["versions"][candidates[0]]


def install_package(meta: dict, node_modules: str):
    """Extract an npm package (with metadata ``meta``) into ``node_modules/<name>``, dependencies included."""
    name = meta["name"]
    dest = os.path.join(node_modules, *name.split("/"))
    if os.path.exists(dest):
        return
    tmp = dest + ".tmp"
    print(f"Downloading {name}@{meta['version']}")
    download_and_extract(meta["dist"]["tarball"], tmp, integrity=meta["dist"].get("integrity"))
    # npm tarballs contain a single top level folder (usually "package")
    inner = os.listdir(tmp)
    shutil.move(os.path.join(tmp, inner[0]), dest)
    shutil.rmtree(tmp)
    for dep, spec in meta.get("dependencies", {}).items():
        if dep.startswith("@typescript/typescript-"):  # native compilers of TypeScript 7+, handled by caller
            continue
        install_package(resolve_range(dep, spec), node_modules)


def choose_node(arch) -> tuple[str, int]:
    """Pick the Node.js used to run the compiled code, returns (folder in langs/javascript, major version)."""
    if os.path.exists("langs/javascript.json"):
        with open("langs/javascript.json") as f:
            js = json.load(f)
        branches = js["branches"]
        names = list(branches)
        print("Choose the Node.js used to run TypeScript:")
        for i, name in enumerate(names):
            print(f"{i + 1}. {name} ({branches[name]['arg']})" + (" (default)" if name == js["default_branch"] else ""))
        while True:
            inp = input("> ").strip()
            if inp == "":
                folder = branches[js["default_branch"]]["arg"]
                break
            if inp.isdigit() and 1 <= int(inp) <= len(names):
                folder = branches[names[int(inp) - 1]]["arg"]
                break
            if inp in branches:
                folder = branches[inp]["arg"]
                break
            print("Invalid input")
    else:
        print("JavaScript (Node.js) is not installed, installing the latest LTS Node.js for TypeScript")
        versions = find_node_versions(arch)
        version = next((v for v, lts in versions if lts), versions[0][0])
        folder = install_node(version, arch)
    major = int(folder.split("-")[1][1:].split(".")[0])
    return folder, major


def main():
    arch = ask_arch()
    print(f"Your architecture is {arch}")
    node_folder, node_major = choose_node(arch)
    response = requests.get(REGISTRY + "typescript")
    response.raise_for_status()
    ts_meta = response.json()
    versions = stable_versions(ts_meta)
    latests = [next(v) for k, v in groupby(versions, lambda x: ".".join(x.split(".")[:2]))][:8]
    mp = {}
    print("Detected versions:")
    for i, a in enumerate(latests):
        print(f"{i + 1}. TypeScript {a}")
        mp[str(i + 1)] = a
        mp[a] = a
        mp[".".join(a.split(".")[:2])] = a
    chosen = choose_versions(mp)
    types_meta = requests.get(REGISTRY + "@types/node")
    types_meta.raise_for_status()
    types_meta = types_meta.json()
    types_versions = [v for v in stable_versions(types_meta) if parse_version(v)[0] == node_major] \
        or stable_versions(types_meta)
    node = f"/langs/javascript/{node_folder}/bin/node"
    dat = {
        "name": "TypeScript",
        "require_compile": True,
        "source_ext": ".ts",
        "exec_name": "{0}.js",
        "compile_cmd": ["/bin/sh", "-c", "{tsc} " + TSC_FLAGS + " \"$0\" 1>&2", "{0}"],
        "exec_cmd": ["/langs/javascript/{node}/bin/node", NODE_STACK, "{0}"],
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
        arg = f"ts-{version}"
        node_modules = f"langs/typescript/{arg}/node_modules"
        meta = ts_meta["versions"][version]
        install_package(meta, node_modules)
        install_package(types_meta["versions"][types_versions[0]], node_modules)
        native = f"@typescript/typescript-linux-{arch}"
        if native in meta.get("dependencies", {}):
            # TypeScript 7+ is a native binary, no Node.js needed for compiling
            install_package(resolve_range(native, meta["dependencies"][native]), node_modules)
            tsc = f"/langs/typescript/{arg}/node_modules/{native}/lib/tsc"
        else:
            tsc = f"{node} /langs/typescript/{arg}/node_modules/typescript/bin/tsc"
        name = "TypeScript" + ".".join(version.split(".")[:2])
        dat["branches"][name] = {
            "arg": arg,
            "tsc": tsc,
            "node": node_folder
        }
        for exe in (node, tsc.split()[0]):
            if exe not in dat["executables"]:
                dat["executables"].append(exe)
        branch_names.append(name)
    write_base_file("typescript", "base_typescript.ts", "\n")
    save_lang_json("typescript", dat, branch_names[0])
    print("TypeScript setup completed")


if __name__ == "__main__":
    main()
