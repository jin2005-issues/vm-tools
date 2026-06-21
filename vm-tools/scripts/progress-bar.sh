#!/bin/bash
# VM Tools - 带进度条的虚拟机操作脚本
# 支持：镜像转换、info查询、进度显示

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 进度条函数
show_progress() {
    local current=$1
    local total=$2
    local message=$3
    local width=40
    
    local percent=$((current * 100 / total))
    local filled=$((width * current / total))
    local empty=$((width - filled))
    
    printf "\r[${GREEN}"
    printf "%${filled}s" | tr ' ' '█'
    printf "${NC}"
    printf "%${empty}s" | tr ' ' '░'
    printf "${NC}] ${BLUE}%3d%%${NC} - %s" "$percent" "$message"
    
    if [ $current -eq $total ]; then
        echo ""
    fi
}

# 格式化大小
format_size() {
    local bytes=$1
    if [ $bytes -ge 1073741824 ]; then
        echo "$(echo "scale=2; $bytes/1073741824" | bc) GB"
    elif [ $bytes -ge 1048576 ]; then
        echo "$(echo "scale=2; $bytes/1048576" | bc) MB"
    elif [ $bytes -ge 1024 ]; then
        echo "$(echo "scale=2; $bytes/1024" | bc) KB"
    else
        echo "$bytes B"
    fi
}

# 获取镜像信息
get_image_info() {
    local image=$1
    
    if [ ! -f "$image" ]; then
        echo -e "${RED}错误: 文件不存在: $image${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}=== 镜像信息: $(basename "$image") ===${NC}"
    echo ""
    
    # 文件大小
    local size=$(stat -c%s "$image")
    echo -e "${GREEN}文件大小:${NC} $(format_size $size)"
    
    # 格式检测
    local format=$(qemu-img info "$image" --output=json 2>/dev/null | grep -o '"format":"[^"]*"' | cut -d'"' -f4 || echo "未知")
    echo -e "${GREEN}格式:${NC} $format"
    
    # 虚拟大小
    local virt_size=$(qemu-img info "$image" 2>/dev/null | grep "virtual size" | grep -oP '\d+' | head -1)
    if [ -n "$virt_size" ]; then
        echo -e "${GREEN}虚拟大小:${NC} $(format_size $virt_size)"
    fi
    
    # 快照
    local snapshots=$(qemu-img snapshot "$image" -l 2>/dev/null | grep -c "Snapshot" || echo "0")
    if [ "$snapshots" -gt 0 ]; then
        echo -e "${GREEN}快照数:${NC} $((snapshots - 2))"
    fi
    
    # qemu-img info
    echo ""
    echo -e "${YELLOW}详细信息:${NC}"
    qemu-img info "$image" 2>/dev/null || echo "无法读取详细信息"
}

# 转换镜像
convert_image() {
    local input=$1
    local output=$2
    local format=$3
    
    if [ ! -f "$input" ]; then
        echo -e "${RED}错误: 输入文件不存在: $input${NC}"
        exit 1
    fi
    
    # 获取输入大小用于进度
    local total_size=$(qemu-img info "$input" 2>/dev/null | grep "virtual size" | grep -oP '\d+' | head -1 || echo "0")
    
    if [ "$total_size" = "0" ]; then
        echo -e "${RED}无法确定镜像大小${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}转换镜像:${NC}"
    echo "  输入: $input"
    echo "  输出: $output"
    echo "  格式: $format"
    echo ""
    
    # 计算区块数
    local block_size=10485760  # 10MB blocks
    local total_blocks=$((total_size / block_size))
    [ $((total_size % block_size)) -gt 0 ] && total_blocks=$((total_blocks + 1))
    
    echo -e "${BLUE}开始转换...${NC}"
    echo ""
    
    # 使用 qemu-img 转换，同时显示进度
    # 通过 dd 和 pv 配合显示进度
    if command -v pv &> /dev/null; then
        qemu-img convert -p -O "$format" "$input" "$output" 2>&1 | while IFS= read -r line; do
            if echo "$line" | grep -q "%"; then
                echo -ne "\r\033[K$line"
            fi
        done
    else
        # 无 pv 时使用简单进度
        qemu-img convert -O "$format" "$input" "$output"
    fi
    
    echo ""
    echo -e "${GREEN}✓ 转换完成: $output${NC}"
    
    # 显示输出文件大小
    if [ -f "$output" ]; then
        local out_size=$(stat -c%s "$output")
        echo -e "${GREEN}输出大小:${NC} $(format_size $out_size)"
    fi
}

# 主函数
main() {
    local command=$1
    shift
    
    case "$command" in
        convert)
            if [ $# -lt 3 ]; then
                echo "用法: $0 convert <输入文件> <输出文件> <目标格式>"
                echo "支持的格式: qcow2, vmdk, raw, vdi, qed"
                exit 1
            fi
            convert_image "$1" "$2" "$3"
            ;;
        info)
            if [ $# -lt 1 ]; then
                echo "用法: $0 info <镜像文件>"
                exit 1
            fi
            get_image_info "$1"
            ;;
        *)
            echo -e "${YELLOW}VM Tools - 虚拟机工具集${NC}"
            echo ""
            echo "用法: $0 <命令> [参数]"
            echo ""
            echo -e "${GREEN}命令:${NC}"
            echo "  convert <输入> <输出> <格式>  - 转换镜像格式"
            echo "  info <镜像文件>                - 查看镜像信息"
            echo ""
            echo -e "${GREEN}示例:${NC}"
            echo "  $0 convert win95.qcow2 win95.vmdk vmdk"
            echo "  $0 info Windows95.qcow2"
            ;;
    esac
}

main "$@"
