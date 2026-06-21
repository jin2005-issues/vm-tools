# QEMU 常用命令参考

## 磁盘镜像操作

### 创建镜像
```bash
# 创建空白镜像
qemu-img create -f qcow2 disk.qcow2 10G

# 从现有镜像创建
qemu-img create -b base.qcow2 -f qcow2 derived.qcow2

# 创建预分配镜像
qemu-img create -f raw -o preallocation=full disk.img 10G
```

### 转换格式
```bash
# qcow2 → VMDK (VMware)
qemu-img convert -O vmdk input.qcow2 output.vmdk

# VMDK → qcow2
qemu-img convert -O qcow2 input.vmdk output.qcow2

# raw → qcow2
qemu-img convert -O qcow2 input.img output.qcow2

# 带进度显示
qemu-img convert -p -O qcow2 input.img output.qcow2
```

### 查看信息
```bash
qemu-img info disk.qcow2
```

## 虚拟机启动

### 基本启动
```bash
# 启动 ISO
qemu-system-i386 -cdrom os.iso -m 512

# 启动硬盘镜像
qemu-system-i386 -hda disk.qcow2 -m 512

# 带图形窗口
qemu-system-i386 -hda disk.qcow2 -m 512 -display gtk
```

### 硬件配置
```bash
# 设置 CPU
qemu-system-i386 -cpu pentium -hda disk.qcow2

# 设置内存
qemu-system-i386 -hda disk.qcow2 -m 256

# 多核 CPU
qemu-system-i386 -hda disk.qcow2 -m 512 -smp 2

# 网络
qemu-system-i386 -hda disk.qcow2 -net nic -net user

# 声卡
qemu-system-i386 -hda disk.qcow2 -soundhw sb16
```

## 快照管理

```bash
# 创建快照
qemu-img snapshot -c backup1 disk.qcow2

# 列出快照
qemu-img snapshot -l disk.qcow2

# 恢复快照
qemu-img snapshot -a backup1 disk.qcow2

# 删除快照
qemu-img snapshot -d backup1 disk.qcow2
```

## 镜像扩容

```bash
# 扩容到 20G
qemu-img resize disk.qcow2 +10G

# 缩小（需先在系统内压缩）
qemu-img resize disk.qcow2 10G
```
