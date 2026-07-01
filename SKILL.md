---
name: vm-tools
description: 虚拟机工具集，支持磁盘镜像转换、VM 管理与进度条显示。当需要以下操作时使用：转换 qcow2/vmdk/img 格式、查看/管理虚拟机、挂载磁盘镜像、调整 VM 配置（内存/CPU）、或任何涉及长时间操作的 VM 任务时自动显示进度条。
---

# VM Tools - 虚拟机工具集

## 进度条样式

所有长时间操作统一使用 ASCII 进度条：

```
[████████████████████░░░░░░░░░░] 55%  Scanning zero blocks  5.2 GB / 10.0 GB
```

进度条颜色：绿色填充块、蓝色百分比，右边显示当前操作状态。

## 核心功能

### 1. 磁盘镜像转换

```bash
bash ~/.openclaw/workspace/skills/vm-tools/scripts/progress-bar.sh convert <input> <output> <format>
```

转换过程中实时显示 `[████████░░░░░░░░░░░░░░░░░] 45%  Converting...` 进度条。

**常用转换：**
| 转换 | 命令 |
|------|------|
| qcow2 → VMDK | `convert input.qcow2 output.vmdk vmdk` |
| VMDK → qcow2 | `convert input.vmdk output.qcow2 qcow2` |
| qcow2 → raw | `convert input.qcow2 output.img raw` |

### 2. 查看镜像信息

```bash
bash ~/.openclaw/workspace/skills/vm-tools/scripts/progress-bar.sh info <image>
```

### 3. 创建虚拟机镜像（带进度条）

```bash
python3 ~/.openclaw/workspace/skills/vm-tools/scripts/create_vm.py <name> --disk-size 20G --format qcow2
# 或 raw / vmdk
```

支持 `--memory <MB>` 和 `--cpus <n>` 参数。

### 4. 清理镜像空洞（带进度条）

分析并 Punch Hole 以回收稀疏镜像中零数据占用的空间：

```bash
# 仅分析
python3 ~/.openclaw/workspace/skills/vm-tools/scripts/punch_holes.py disk.qcow2

# 分析 + 回收空间
python3 ~/.openclaw/workspace/skills/vm-tools/scripts/punch_holes.py disk.qcow2 --punch
```

### 5. 挂载 qcow2 镜像（只读）

```bash
sudo bash ~/.openclaw/workspace/skills/vm-tools/scripts/mount-qcow2.sh <image> [mount_point]
```

## 参考文档

- **QEMU 常用命令**: 查看 `references/qemu-commands.md`
- **Parallels 配置**: 查看 `references/parallels-config.md`
