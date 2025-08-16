# 使用一个官方的 Python 镜像作为我们的基础环境
FROM python:3.11-slim

# 设置工作目录，后续的命令都在这个目录下执行
WORKDIR /app

# (后续我们会在这里添加复制文件、安装依赖等指令)

# 容器启动时默认执行的命令
# (例如，启动我们的FastAPI服务)
# CMD ["poetry", "run", "uvicorn", "src.financial_analyst.api.main:app", "--host", "0.0.0.0", "--port", "80"]