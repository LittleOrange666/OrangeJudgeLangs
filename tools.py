import os
import tarfile
from io import BytesIO
from subprocess import Popen, PIPE

import requests
from tqdm import tqdm


def extract_with_progress(file, output_dir):
    with tarfile.open(fileobj=file, mode="r:*") as tar:
        members = tar.getmembers()
        total_files = len(members)

        with tqdm(total=total_files, desc="Extracting", unit="file") as pbar:
            for member in members:
                tar.extract(member, output_dir)
                pbar.update(1)


def download_and_extract(link, target):
    response = requests.get(link, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024
    progress_bar = tqdm(total=total_size, desc="Downloading", unit='iB', unit_scale=True)

    file_obj = BytesIO()
    for data in response.iter_content(block_size):
        progress_bar.update(len(data))
        file_obj.write(data)
    progress_bar.close()

    file_obj.seek(0)
    extract_with_progress(file_obj, target)


class Builder:
    def __init__(self):
        os.makedirs("langs", exist_ok=True)
        self.proc = Popen(["docker", "run", "--rm", "-i", "-v", f"{os.getcwd()}/langs:/langs",
                           "littleorange666/builder", "bash"], stdin=PIPE, text=True)

    def send_cmd(self, cmd):
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.send_cmd("exit")
        self.proc.stdin.close()
        self.proc.wait()
