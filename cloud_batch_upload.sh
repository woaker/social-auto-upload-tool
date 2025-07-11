#!/bin/bash

# 云服务器批量上传脚本
# 使用优化的浏览器配置上传视频到抖音

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

# 显示帮助信息
show_help() {
    echo "云服务器批量上传脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --date DATE       指定视频所在日期目录，格式：YYYY-MM-DD (必填)"
    echo "  --schedule        使用定时发布 (默认为立即发布)"
    echo "  --test-only       仅测试连接，不上传视频"
    echo "  --help            显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 --date 2025-07-03                # 立即发布2025-07-03目录下的视频"
    echo "  $0 --date 2025-07-03 --schedule     # 定时发布2025-07-03目录下的视频"
    echo "  $0 --test-only                      # 仅测试抖音连接"
    echo ""
}

# 检查系统环境
check_environment() {
    log_info "检查系统环境..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3未安装，请先安装Python3"
        exit 1
    fi
    
    # 检查pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3未安装，请先安装pip3"
        exit 1
    fi
    
    # 检查playwright
    if ! python3 -c "import playwright" &> /dev/null; then
        log_warning "未检测到playwright，正在安装..."
        pip3 install playwright
        python3 -m playwright install chromium
    fi
    
    # 检查Chrome
    if ! command -v google-chrome &> /dev/null; then
        log_warning "未检测到Google Chrome，尝试安装..."
        
        # 检测系统类型
        if [ -f /etc/debian_version ]; then
            # Debian/Ubuntu
            log_info "检测到Debian/Ubuntu系统"
            wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
            echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
            sudo apt update
            sudo apt install -y google-chrome-stable
        elif [ -f /etc/redhat-release ]; then
            # CentOS/RHEL
            log_info "检测到CentOS/RHEL系统"
            sudo yum install -y https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
        else
            log_error "不支持的系统类型，请手动安装Google Chrome"
            exit 1
        fi
    fi
    
    # 检查视频目录
    if [ ! -d "videoFile" ]; then
        log_warning "未找到videoFile目录，正在创建..."
        mkdir -p videoFile
    fi
    
    # 检查cookie目录
    if [ ! -d "cookiesFile" ]; then
        log_warning "未找到cookiesFile目录，正在创建..."
        mkdir -p cookiesFile
    fi
    
    log_success "环境检查完成"
}

# 测试抖音连接
test_connection() {
    log_info "测试抖音连接..."
    
    # 检查连接测试脚本
    if [ ! -f "douyin_connection_fix.py" ]; then
        log_error "未找到连接测试脚本 douyin_connection_fix.py"
        exit 1
    fi
    
    # 运行连接测试
    python3 douyin_connection_fix.py
    
    if [ $? -ne 0 ]; then
        log_error "抖音连接测试失败，请检查网络和Cookie"
        exit 1
    fi
    
    log_success "抖音连接测试成功"
}

# 批量上传视频
batch_upload() {
    local date_str=$1
    local schedule=$2
    
    log_info "开始批量上传视频..."
    
    # 检查日期格式
    if ! [[ $date_str =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        log_error "日期格式错误，请使用YYYY-MM-DD格式"
        exit 1
    fi
    
    # 检查视频目录
    local video_dir="videoFile/$date_str"
    if [ ! -d "$video_dir" ]; then
        log_error "视频目录不存在: $video_dir"
        exit 1
    fi
    
    # 检查视频文件
    local video_count=$(find "$video_dir" -type f -name "*.mp4" -o -name "*.webm" -o -name "*.avi" -o -name "*.mov" -o -name "*.mkv" -o -name "*.flv" | wc -l)
    if [ "$video_count" -eq 0 ]; then
        log_error "在目录 $video_dir 中没有找到视频文件"
        exit 1
    fi
    
    log_info "找到 $video_count 个视频文件"
    
    # 检查上传脚本
    if [ ! -f "douyin_enhanced_uploader.py" ]; then
        log_error "未找到上传脚本 douyin_enhanced_uploader.py"
        exit 1
    fi
    
    # 运行上传脚本
    if [ "$schedule" = true ]; then
        log_info "使用定时发布模式"
        python3 douyin_enhanced_uploader.py --date "$date_str" --schedule
    else
        log_info "使用立即发布模式"
        python3 douyin_enhanced_uploader.py --date "$date_str"
    fi
    
    if [ $? -eq 0 ]; then
        log_success "批量上传完成"
    else
        log_error "批量上传失败"
        exit 1
    fi
}

# 主函数
main() {
    # 解析参数
    local date_str=""
    local schedule=false
    local test_only=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --date)
                date_str="$2"
                shift 2
                ;;
            --schedule)
                schedule=true
                shift
                ;;
            --test-only)
                test_only=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 检查必填参数
    if [ "$test_only" = false ] && [ -z "$date_str" ]; then
        log_error "缺少必填参数: --date"
        show_help
        exit 1
    fi
    
    # 显示配置信息
    echo "=================================="
    echo "    云服务器批量上传脚本"
    echo "=================================="
    echo ""
    
    if [ "$test_only" = true ]; then
        log_info "仅测试抖音连接"
    else
        log_info "批量上传配置:"
        log_info "  日期目录: $date_str"
        log_info "  发布模式: $([ "$schedule" = true ] && echo "定时发布" || echo "立即发布")"
    fi
    echo ""
    
    # 检查环境
    check_environment
    
    # 测试连接
    test_connection
    
    # 如果仅测试连接，则退出
    if [ "$test_only" = true ]; then
        exit 0
    fi
    
    # 批量上传
    batch_upload "$date_str" "$schedule"
}

# 运行主函数
main "$@" 