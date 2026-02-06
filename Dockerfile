# 使用国内 DaoCloud 镜像源加速下载 (原: python:3.11-slim)
FROM docker.m.daocloud.io/python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.0.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONPATH="/app/src"

# 将 Poetry 添加到 PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# 设置工作目录
WORKDIR /app

# 安装系统依赖
# 替换 apt 源为阿里云镜像以解决网络超时问题
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# curl: 用于下载 poetry
# build-essential: 某些 python 库编译需要
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Poetry (改为使用 pip + 国内镜像安装，解决官方脚本网络连接问题)
RUN pip install --no-cache-dir poetry==${POETRY_VERSION} -i https://mirrors.aliyun.com/pypi/simple/

# 复制依赖定义文件
COPY pyproject.toml poetry.lock* ./

# 安装依赖 (不安装 dev 依赖，不安装当前项目本身作为包)
RUN poetry install --no-root --only main --no-interaction --no-ansi

# 复制项目代码
COPY src/ ./src/
COPY frontend/ ./frontend/

# 创建必要的缓存目录
RUN mkdir -p cache_data faiss_index

# 暴露端口 (8000: API, 8501: Streamlit)
EXPOSE 8000 8501

# 默认启动命令（可以在 docker-compose 中覆盖）
CMD ["uvicorn", "financial_report_ai_assistant.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
