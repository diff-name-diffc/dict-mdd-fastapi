#!/bin/bash
set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 加载环境变量
if [ ! -f ".env" ]; then
    log_error ".env 文件不存在"
    exit 1
fi

log_info "加载 .env 环境变量..."
export $(cat .env | grep -v '^#' | xargs)

# 检查必要的环境变量
if [ -z "$DEPLOY_SSH_HOST" ]; then
    log_error "DEPLOY_SSH_HOST 环境变量未设置"
    log_info "请在 .env.demo 中添加以下配置："
    echo "DEPLOY_SSH_HOST=your-server-ip"
    echo "DEPLOY_SSH_USER=your-username"
    echo "DEPLOY_SSH_PASSWORD=your-password"
    exit 1
fi

if [ -z "$DEPLOY_SSH_USER" ]; then
    log_error "DEPLOY_SSH_USER 环境变量未设置"
    exit 1
fi

if [ -z "$DEPLOY_SSH_PASSWORD" ]; then
    log_error "DEPLOY_SSH_PASSWORD 环境变量未设置"
    exit 1
fi

# 配置部署参数
REMOTE_HOST="$DEPLOY_SSH_HOST"
REMOTE_USER="$DEPLOY_SSH_USER"
REMOTE_PASSWORD="$DEPLOY_SSH_PASSWORD"
REMOTE_DIR="/home/jk/english_basic_api"
LOCAL_DIR="$(pwd)"

log_info "部署配置:"
echo "  远程主机: $REMOTE_HOST"
echo "  远程用户: $REMOTE_USER"
echo "  远程目录: $REMOTE_DIR"
echo "  本地目录: $LOCAL_DIR"

# 检查sshpass是否安装
if ! command -v sshpass &> /dev/null; then
    log_warning "sshpass 未安装，正在安装..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install sshpass
        else
            log_error "请先安装 Homebrew 或手动安装 sshpass"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt-get install -y sshpass || sudo yum install -y sshpass
    fi
fi

# 检查rsync是否安装
if ! command -v rsync &> /dev/null; then
    log_error "rsync 未安装，请先安装 rsync"
    exit 1
fi

# 定义排除的文件和目录
EXCLUDE_PATTERNS=(
    ".git"
    ".gitignore"
    ".venv"
    "__pycache__"
    "*.pyc"
    "*.pyo"
    "*.pyd"
    ".Python"
    "*.so"
    "*.egg"
    "*.egg-info"
    "dist"
    "build"
    ".pytest_cache"
    ".ruff_cache"
    ".mypy_cache"
    ".coverage"
    "htmlcov"
    ".DS_Store"
    ".idea"
    ".vscode"
    "*.log"
    "logs/*"
    "uploads/*"
    ".env.dev"
    ".env.example"
    "*.bak"
    "*.tmp"
    "resources/*"
)

# 构建 rsync 排除参数
EXCLUDE_ARGS=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude=$pattern"
done

log_info "开始同步代码到远程服务器..."

# 使用 rsync 同步代码
# -a: 归档模式，保持文件属性
# -v: 显示详细信息
# -z: 压缩传输
# --delete: 删除远程服务器上本地不存在的文件
# --progress: 显示传输进度
sshpass -p "$REMOTE_PASSWORD" rsync -avz --delete $EXCLUDE_ARGS \
    --progress \
    -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
    "$LOCAL_DIR/" \
    "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"

if [ $? -eq 0 ]; then
    log_success "代码同步完成"
else
    log_error "代码同步失败"
    exit 1
fi

log_info "开始远程部署..."

# 远程执行部署命令
sshpass -p "$REMOTE_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    "$REMOTE_USER@$REMOTE_HOST" << 'ENDSSH'

# 设置远程工作目录
cd /home/jk/english_basic_api

# 设置生产环境资源路径
export MDD_RESOURCE_DIR=/home/jk/resources/english/us-uk
export MDD_DB_DIR=/home/jk/resources/english/us-uk

echo "========================================="
echo "安装系统依赖..."
echo "========================================="

# 安装 python-lzo 编译所需的 LZO 开发库
apt-get update && apt-get install -y liblzo2-dev

echo "========================================="
echo "开始安装 Python 依赖..."
echo "========================================="

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "[WARNING] uv 未安装，正在安装..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.bashrc || source ~/.zshrc
fi

# 安装依赖
uv sync

if [ $? -eq 0 ]; then
    echo "[SUCCESS] 依赖安装完成"
else
    echo "[ERROR] 依赖安装失败"
    exit 1
fi

echo "========================================="
echo "检查并停止旧进程..."
echo "========================================="

# 查找并停止旧的 mdd_api.py 进程
OLD_PID=$(ps aux | grep 'uv run mdd_api.py' | grep -v grep | awk '{print $2}')

if [ ! -z "$OLD_PID" ]; then
    echo "[INFO] 发现旧进程 PID: $OLD_PID，正在停止..."
    kill -15 $OLD_PID
    sleep 6

    # 检查进程是否已停止
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "[WARNING] 进程未响应，强制终止..."
        kill -9 $OLD_PID
        sleep 1
    fi
    echo "[SUCCESS] 旧进程已停止"
else
    echo "[INFO] 未发现运行中的旧进程"
fi

echo "========================================="
echo "启动服务..."
echo "========================================="

# 创建日志目录
mkdir -p logs

# 后台启动服务，并将日志输出到文件
nohup uv run mdd_api.py > logs/app.log 2>&1 &

# 记录进程 PID
APP_PID=$!
echo "[SUCCESS] 服务已启动，PID: $APP_PID"

# 等待服务启动
sleep 2

# 检查进程是否还在运行
if ps -p $APP_PID > /dev/null 2>&1; then
    echo "[SUCCESS] 服务运行正常"
    echo "========================================="
    echo "实时日志（按 Ctrl+C 退出日志查看，服务将继续运行）："
    echo "========================================="

    # 实时显示日志
    tail -f logs/app.log
else
    echo "[ERROR] 服务启动失败，查看日志："
    tail -n 50 logs/app.log
    exit 1
fi

ENDSSH

