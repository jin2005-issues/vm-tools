---
name: vm-tools
description: 虚拟机工具集，支持磁盘镜像转换、VM 管理与进度条显示。当需要以下操作时使用：转换 qcow2/vmdk/img 格式、查看/管理虚拟机、挂载磁盘镜像、调整 VM 配置（内存/CPU）、或任何涉及长时间操作的 VM 任务时自动显示进度条。
---

# VM Tools - 虚拟机工具集

## 核心功能

### 1. 磁盘镜像转换

```bash
# 使用 progress-bar 脚本转换，支持 qcow2/vmdk/raw 互转
bash ~/.openclaw/workspace/skills/vm-tools/scripts/progress-bar.sh convert <input> <output> <format>
```

**常用转换：**
| 转换 | 命令 |
|------|------|
| qcow2 → VMDK | `convert input.qcow2 output.vmdk vmdk` |
| VMDK → qcow2 | `convert input.vmdk output.qcow2 qcow2` |
| qcow2 → raw | `convert input.qcow2 output.img raw` |

### 2. 进度条使用

所有长时间操作都会自动显示 ASCII 进度条：

```
[████████░░░░░░░░░░░░░░░░] 40% - 正在处理区块 8192/20480
```

### 3. 查看镜像信息

```bash
bash ~/.openclaw/workspace/skills/vm-tools/scripts/progress-bar.sh info <image>
```

### 4. 挂载 qcow2 镜像（只读）

```bash
sudo bash ~/.openclaw/workspace/skills/vm-tools/scripts/mount-qcow2.sh <image> [mount_point]
```

## 参考文档

- **QEMU 常用命令**: 查看 `references/qemu-commands.md`
- **Parallels 配置**: 查看 `references/parallels-config.md`
