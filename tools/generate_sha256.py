import os
import hashlib
from tkinter import Tk
from tkinter.filedialog import askopenfilename


def generate_sha256_file(file_path: str):
    """
    为给定路径的文件生成 SHA256 校验值，并在同一文件夹下生成同名的 .sha256 文件
    :param file_path: 文件的完整路径
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # 计算文件的 SHA256 值
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    sha256_hash = sha256.hexdigest()

    # 生成 .sha256 文件路径
    sha256_file_path = f"{file_path}.sha256"

    # 将 SHA256 值写入 .sha256 文件
    with open(sha256_file_path, "w") as sha256_file:
        sha256_file.write(sha256_hash)

    print(f"SHA256 file generated: {sha256_file_path}")
    print(f"SHA256 hash: {sha256_hash}")


if __name__ == "__main__":
    Tk().withdraw()  # hide main window
    print("Please select a file to generate its SHA256...")
    file_path = askopenfilename()

    if file_path:
        try:
            generate_sha256_file(file_path)
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("File not selected, now exit.")