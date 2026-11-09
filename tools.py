import base64
import hashlib
import json
import os
import platform
import random
import tarfile
from io import BytesIO

import requests
from tqdm import tqdm


def extract_with_progress(file, output_dir):
    with tarfile.open(fileobj=file, mode="r:*") as tar:
        members = tar.getmembers()
        total_files = len(members)
        # "data" filter refuses absolute paths / links escaping output_dir (default since Python 3.14)
        extra = {"filter": "data"} if hasattr(tarfile, "data_filter") else {}

        with tqdm(total=total_files, desc="Extracting", unit="file") as pbar:
            for member in members:
                tar.extract(member, output_dir, **extra)
                pbar.update(1)


def check_integrity(data, integrity):
    """Verify ``data`` against a Subresource-Integrity string such as npm's ``sha512-<base64>``."""
    algo, _, expected = integrity.partition("-")
    digest = base64.b64encode(hashlib.new(algo, data).digest()).decode()
    if digest != expected:
        raise ValueError(f"Integrity mismatch: expected {integrity}, got {algo}-{digest}")


def download_and_extract(link, target, sha256=None, integrity=None):
    response = requests.get(link, stream=True)
    response.raise_for_status()
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024 * 64
    progress_bar = tqdm(total=total_size, desc="Downloading", unit='iB', unit_scale=True)

    file_obj = BytesIO()
    for data in response.iter_content(block_size):
        progress_bar.update(len(data))
        file_obj.write(data)
    progress_bar.close()

    if sha256 is not None:
        digest = hashlib.sha256(file_obj.getbuffer()).hexdigest()
        if digest.lower() != sha256.lower():
            raise ValueError(f"Checksum mismatch for {link}: expected {sha256}, got {digest}")
    if integrity is not None:
        check_integrity(file_obj.getbuffer(), integrity)

    file_obj.seek(0)
    extract_with_progress(file_obj, target)


def ask_arch() -> str:
    """Detect the machine architecture, returns "x64" or "arm64"."""
    print("Try to detect your architecture")
    plat = platform.machine()
    if plat in ("x86_64", "AMD64", "amd64"):
        return "x64"
    if plat in ("aarch64", "arm64"):
        return "arm64"
    print("Unknown architecture detected")
    while True:
        print("""please choose your Architecture:
1. x64 (default)
2. arm64""")
        table = {
            "1": "x64",
            "2": "arm64"
        }
        arch = input("> ").strip()
        if arch == "":
            return "x64"
        if arch in table:
            return table[arch]
        if arch in table.values():
            return arch
        print("Invalid input")


def choose_versions(mp: dict) -> list[str]:
    """Ask the user for comma separated keys of ``mp``, returns the chosen keys (deduplicated, in order)."""
    while True:
        print("Please input the versions you want to download, separated by comma:")
        inp = input("> ")
        chosen = []
        for x in inp.split(","):
            x = x.strip()
            if x and x not in chosen:
                chosen.append(x)
        if not chosen:
            print("Please choose at least one version")
            continue
        for x in chosen:
            if x not in mp:
                print("Invalid version: " + x)
                break
        else:
            return chosen


def save_lang_json(name: str, dat: dict, default_branch: str):
    """
    Write ``langs/<name>.json``. Branches and executables already present in an existing file are kept,
    so installing more versions later does not remove the old ones.
    """
    path = f"langs/{name}.json"
    if os.path.exists(path):
        with open(path) as f:
            old = json.load(f)
        branches = dict(old.get("branches", {}))
        branches.update(dat["branches"])
        dat["branches"] = branches
        executables = list(old.get("executables", []))
        for exe in dat.get("executables", []):
            if exe not in executables:
                executables.append(exe)
        dat["executables"] = executables
        if old.get("default_branch") in branches:
            default_branch = old["default_branch"]
    dat["default_branch"] = default_branch
    with open(path, "w") as f:
        json.dump(dat, f, indent=4)


def write_base_file(name: str, filename: str, content: str):
    os.makedirs(f"langs/{name}", exist_ok=True)
    with open(f"langs/{name}/{filename}", "w") as f:
        f.write(content)


class Builder:
    def __init__(self):
        os.makedirs("langs", exist_ok=True)
        self.container_id = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=12))
        os.system(f"docker run -v ./langs:/langs -d --name {self.container_id} --rm --entrypoint sleep littleorange666/builder infinity")

    def send_cmd(self, cmd):
        os.system(f"docker exec -it {self.container_id} {cmd}")

    def send_cmd_in(self, cmd, path):
        os.system(f"docker exec -it -w {path} {self.container_id} {cmd}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.system(f"docker stop {self.container_id}")
