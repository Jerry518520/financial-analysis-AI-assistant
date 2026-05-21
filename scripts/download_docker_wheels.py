"""
预下载 Docker 构建所需的大文件到本地，避免构建时下载慢的问题。

用法（任选一种）：
  python scripts/download_docker_wheels.py
  双击 download_wheels.bat

下载完成后，docker-compose build 会从本地 COPY 文件，不再走网络。
不下载也能构建，只是 torch 会在构建时从镜像下载（较慢）。
"""
import subprocess
import sys
import os
from pathlib import Path

WHEEL_DIR = Path(__file__).parent.parent / "docker" / "wheels"

# 需要预下载的大文件（URL -> 本地文件名）
LARGE_WHEELS = {
    "https://mirrors.aliyun.com/pytorch-wheels/cu126/torch-2.10.0%2Bcu126-cp311-cp311-manylinux_2_28_x86_64.whl":
        "torch-2.10.0+cu126-cp311-cp311-manylinux_2_28_x86_64.whl",
}


def download_file(url: str, dest: Path):
    """下载文件，支持断点续传"""
    if dest.exists():
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  ✅ 已存在: {dest.name} ({size_mb:.0f} MB)，跳过")
        return True

    print(f"  ⬇️  正在下载: {dest.name}")
    print(f"     URL: {url}")

    # 尝试用 aria2c（更快），否则用 curl，最后用 python
    for tool, cmd in [
        ("aria2c", ["aria2c", "-x", "16", "-s", "16", "-k", "10M",
                     "-d", str(dest.parent), "-o", dest.name, url]),
        ("curl", ["curl", "-L", "-#", "-o", str(dest), url]),
    ]:
        if _has_tool(tool):
            print(f"     使用 {tool} 下载...")
            result = subprocess.run(cmd)
            if result.returncode == 0 and dest.exists():
                size_mb = dest.stat().st_size / (1024 * 1024)
                print(f"  ✅ 下载完成: {dest.name} ({size_mb:.0f} MB)")
                return True
            else:
                print(f"  ⚠️  {tool} 下载失败，尝试下一种方式...")
                if dest.exists():
                    dest.unlink()

    # Python fallback
    print("     使用 Python 下载...")
    try:
        import urllib.request
        urllib.request.urlretrieve(url, str(dest))
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  ✅ 下载完成: {dest.name} ({size_mb:.0f} MB)")
        return True
    except Exception as e:
        print(f"  ❌ 下载失败: {e}")
        return False


def _has_tool(name: str) -> bool:
    try:
        subprocess.run([name, "--version"], capture_output=True)
        return True
    except FileNotFoundError:
        return False


def main():
    WHEEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📦 预下载 Docker 构建依赖到: {WHEEL_DIR}\n")

    success = 0
    for url, filename in LARGE_WHEELS.items():
        dest = WHEEL_DIR / filename
        if download_file(url, dest):
            success += 1

    print(f"\n{'='*50}")
    print(f"完成: {success}/{len(LARGE_WHEELS)} 个文件")
    if success == len(LARGE_WHEELS):
        print("✅ 所有文件就绪，现在可以运行:")
        print("   docker-compose build")
        print("   (构建时将从本地 COPY，不再下载大文件)")


if __name__ == "__main__":
    main()
