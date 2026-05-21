"""
Poetry 安装后的 CUDA PyTorch 补丁脚本。

问题：poetry.lock 锁定的是 PyPI 上的 CPU 版 torch (2.10.0)，
     但 RAG 向量化必须用 CUDA GPU。

用法：
  poetry install
  poetry run python scripts/install_cuda_torch.py

或使用 poe 任务：
  poetry run poe install-cuda-torch
"""
import subprocess
import sys

TORCH_VERSION = "2.10.0+cu126"
MIRROR_URL = "https://mirrors.aliyun.com/pytorch-wheels/cu126/"


def _check_torch():
    """通过子进程检查 torch 状态，避免在本进程中导入 torch C 扩展。"""
    result = subprocess.run(
        [sys.executable, "-c",
         "import torch; print(torch.__version__); print(torch.cuda.is_available())"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None, False
    lines = result.stdout.strip().split("\n")
    version = lines[0] if lines else ""
    cuda = lines[1].strip().lower() == "true" if len(lines) > 1 else False
    return version, cuda


def main():
    version, cuda = _check_torch()

    if version is None:
        print("未检测到 torch，请先运行 poetry install。")
        sys.exit(1)

    print(f"当前 torch 版本: {version}")
    print(f"CUDA 可用: {cuda}")

    if "+cu" in version and cuda:
        print("已是 CUDA 版本，无需修改。")
        return

    print(f"\n正在安装 CUDA 版 torch ({TORCH_VERSION})...")
    cmd = [
        sys.executable, "-m", "pip", "install",
        f"torch=={TORCH_VERSION}",
        "-f", MIRROR_URL,
        "--no-deps",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"安装失败:\n{result.stderr}")
        sys.exit(1)

    # 通过子进程验证，不 reload C 扩展
    version, cuda = _check_torch()
    print(f"\n安装完成！torch 版本: {version}")
    print(f"CUDA 可用: {cuda}")
    if not cuda:
        print("警告: CUDA 仍不可用，请检查 NVIDIA 驱动和 CUDA Toolkit。")


if __name__ == "__main__":
    main()
