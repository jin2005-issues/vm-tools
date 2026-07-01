#!/bin/bash
# qcow2 镜像挂载脚本（只读）
# 用法: mount-qcow2.sh <镜像文件> [挂载点]

set -e

IMAGE=$1
MOUNT_POINT=${2:-"/tmp/qcow2_mount_$$"}

if [ -z "$IMAGE" ]; then
    echo "用法: $0 <qcow2镜像> [挂载点]"
    exit 1
fi

if [ ! -f "$IMAGE" ]; then
    echo "错误: 文件不存在: $IMAGE"
    exit 1
fi

# 检查 nbd 模块
if ! lsmod | grep -q nbd; then
    echo "加载 nbd 模块..."
    sudo modprobe nbd max_part=8
fi

# 找到可用 nbd 设备
NBD_DEV=""
for i in $(seq 0 7); do
    if ! ls /sys/block/nbd$i/pid 2>/dev/null; then
        NBD_DEV="/dev/nbd$i"
        break
    fi
done

if [ -z "$NBD_DEV" ]; then
    echo "错误: 没有可用的 nbd 设备"
    exit 1
fi

echo "使用设备: $NBD_DEV"

# 连接镜像
sudo qemu-nbd -r -c "$NBD_DEV" "$IMAGE"

# 等待设备就绪
sleep 1

# 列出分区
echo ""
echo "可用分区:"
ls -la "${NBD_DEV}"*

# 创建挂载点
sudo mkdir -p "$MOUNT_POINT"

# 挂载第一个分区（只读）
echo ""
echo "挂载分区 1 到 $MOUNT_POINT (只读)..."
sudo mount -o ro "${NBD_DEV}p1" "$MOUNT_POINT" 2>/dev/null || \
sudo mount -o ro "${NBD_DEV}1" "$MOUNT_POINT" 2>/dev/null || {
    echo "挂载失败，尝试手动挂载"
    sudo qemu-nbd -d "$NBD_DEV"
    exit 1
}

echo ""
echo "✓ 已挂载到: $MOUNT_POINT"
echo "使用完毕后运行: sudo umount '$MOUNT_POINT' && sudo qemu-nbd -d '$NBD_DEV'"
echo ""

# 显示内容
echo "镜像内容:"
ls -la "$MOUNT_POINT"
