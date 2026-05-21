# 使用国内 DaoCloud 镜像源加速下载 (原: python:3.11-slim)
FROM docker.m.daocloud.io/python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/src" \
    HF_ENDPOINT=https://hf-mirror.com \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

# 设置工作目录
WORKDIR /app

# 安装系统依赖
# 替换 apt 源为阿里云镜像以解决网络超时问题
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# build-essential: 某些 python 库编译需要
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ====== 第一层：PyTorch CUDA（独立缓存层，版本变更时才重建）======
# 优先从本地 docker/wheels/ 安装（需先运行 scripts/download_docker_wheels.py）
# 若本地无 wheel 则从阿里云镜像下载
COPY docker/wheels/ /tmp/wheels/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-deps /tmp/wheels/torch-2.10.0+cu126-cp311-cp311-manylinux_2_28_x86_64.whl \
    || pip install --no-deps https://mirrors.aliyun.com/pytorch-wheels/cu126/torch-2.10.0%2Bcu126-cp311-cp311-manylinux_2_28_x86_64.whl

# ====== 第二层：其余 Python 依赖（requirements-docker.txt 不含 torch）======
# poetry export --without-hashes --only main 生成，排除 dev 依赖
# --timeout 120: 阿里云镜像偶发超时，给足等待时间
COPY requirements-docker.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 120 --retries 5 -r requirements-docker.txt

# ====== 第三层：项目代码（变更最频繁，放最后）======
COPY src/ ./src/

# 创建必要的缓存目录
RUN mkdir -p cache_data faiss_index

# 暴露端口 (8000: API)
EXPOSE 8000

# 默认启动命令（可以在 docker-compose 中覆盖）
CMD ["uvicorn", "financial_report_ai_assistant.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
