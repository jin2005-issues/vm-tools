#!/usr/bin/env python3
"""
VM Creator - Create new virtual machines and disk images

Usage:
    python3 create_vm.py <vm_name> --disk-size <size> [--format qcow2|raw] [--memory <MB>] [--cpus <n>]
"""

import os
import sys
import argparse
import struct
import shutil

# Progress bar colours
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
RED = '\033[0;31m'
NC = '\033[0m'
BAR_WIDTH = 38


def make_progress_bar(current, total, width=BAR_WIDTH):
    pct = min(100, max(0, int(current * 100 // max(total, 1))))
    filled = width * current // max(total, 1)
    empty = width - filled
    return f"[{GREEN}{'█' * filled}{NC}{'░' * empty}] {BLUE}{pct:3d}%{NC}"


def show_progress(current, total, suffix="", width=BAR_WIDTH):
    bar = make_progress_bar(current, total, width)
    line = f"\r{bar}  {suffix}"
    term_w = shutil.get_terminal_size().columns or 90
    sys.stdout.write(line[:term_w])
    sys.stdout.flush()


def format_bytes(size):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def parse_size(size_str):
    """Parse size string like '10G', '512M'"""
    size_str = size_str.upper().strip()
    multipliers = {
        'B': 1,
        'K': 1024,
        'M': 1024**2,
        'G': 1024**3,
        'T': 1024**4
    }

    for suffix, mult in multipliers.items():
        if size_str.endswith(suffix):
            num = size_str[:-len(suffix)]
            try:
                return int(float(num) * mult)
            except ValueError:
                pass

    # Just a number
    try:
        return int(size_str)
    except ValueError:
        raise ValueError(f"Invalid size: {size_str}")


def create_qcow2(filepath, size):
    """Create a QCOW2 image"""
    print(f"{YELLOW}📦 Creating QCOW2 image...{NC}")

    cluster_bits = 16
    cluster_size = 65536  # 64KB

    with open(filepath, 'wb') as f:
        # QCOW2 header (72 bytes minimum)
        header = bytearray(72)

        # Magic (4 bytes)
        header[0:4] = struct.pack('>I', 0x514649FB)

        # Version (4 bytes) = 3
        header[4:8] = struct.pack('>I', 3)

        # Backing file offset (8 bytes) = 0
        header[8:16] = struct.pack('>Q', 0)

        # L2 table size (4 bytes)
        header[16:20] = struct.pack('>I', 1)  # 1 cluster

        # Cluster bits (4 bytes) = 16
        header[20:24] = struct.pack('>I', cluster_bits)

        # Cluster size (4 bytes) = 65536
        header[24:28] = struct.pack('>I', cluster_size)

        # Page size (4 bytes)
        header[28:32] = struct.pack('>I', 4096)

        # Virtual disk size (8 bytes)
        header[32:40] = struct.pack('>Q', size)

        # Write header
        f.write(header)
        show_progress(1, 4, "Writing header")

        # Write refcount table (1 cluster, all zeros = all clusters unallocated)
        refcount = bytearray(cluster_size)
        f.write(refcount)
        show_progress(2, 4, "Writing refcount table")

        # Write L1 table (sparse, points to L2 tables)
        # For simplicity, just write the minimum L1 table
        l1 = bytearray(32)  # 4 entries * 8 bytes
        f.write(l1)
        show_progress(3, 4, "Writing L1 table")

        # Write initial L2 table (all zeros = all data unallocated)
        l2 = bytearray(cluster_size)
        f.write(l2)
        show_progress(4, 4, "Writing L2 table")

    print()  # newline after progress bar
    print(f"   {GREEN}✓{NC} Created: {filepath}")
    print(f"   Size: {format_bytes(size)}")
    print(f"   Format: QCOW2 (sparse)")


def create_raw(filepath, size):
    """Create a raw disk image (sparse)"""
    print(f"{YELLOW}📦 Creating raw image (sparse)...{NC}")

    block_mb = 64  # 64 MB per progress step
    block_size = block_mb * 1024 * 1024
    total_blocks = (size + block_size - 1) // block_size

    with open(filepath, 'wb') as f:
        for b in range(total_blocks):
            # Seek to end of this block and write one null byte (sparse)
            f.seek((b + 1) * block_size - 1)
            f.write(b'\0')
            show_progress(b + 1, total_blocks, f"Seeking block {b + 1}/{total_blocks}  {format_bytes((b + 1) * block_size)} / {format_bytes(size)}")

    print()  # newline after progress bar
    print(f"   {GREEN}✓{NC} Created: {filepath}")
    print(f"   Size: {format_bytes(size)}")
    print(f"   Format: RAW (sparse)")


# Image formats
FORMATS = ['qcow2', 'raw', 'vmdk']


def create_vmdk(filepath, size):
    """Create a VMDK image (simplified)"""
    print(f"{YELLOW}📦 Creating VMDK image...{NC}")

    block_size = 64 * 1024 * 1024
    n_blocks = (size + block_size - 1) // block_size

    with open(filepath, 'wb') as f:
        show_progress(1, n_blocks + 1, "Writing VMDK descriptor")
        descriptor = f"""# Disk descriptorFile
version=1
CID=12345678
parentCID=ffffffff
createType="monolithicSparse"

# Extent description
RW {size // 512} SPARSE "{filepath}"

# The disk Data Baseline
ddb.adapterType = "ide"
ddb.geometry.cylinders = "16383"
ddb.geometry.heads = "16"
ddb.geometry.sectors = "63"
ddb.longContentID = "12345678901234567890123456789012"
ddb.virtualHWVersion = "4"
"""
        f.write(descriptor.encode())

        for b in range(n_blocks):
            f.seek((b + 1) * block_size - 1)
            f.write(b'\0')
            show_progress(b + 2, n_blocks + 1,
                          f"Allocating extent {b + 1}/{n_blocks}  {format_bytes((b + 1) * block_size)} / {format_bytes(size)}")

    print()
    print(f"   {GREEN}✓{NC} Created: {filepath}")
    print(f"   Size: {format_bytes(size)}")
    print(f"   Format: VMDK (sparse)")

def create_vm_config(vm_name, disk_path, disk_size, memory=1024, cpus=1):
    """Create VM configuration file"""
    config = f"""# VM Configuration for {vm_name}
# Generated by VM Tools

[general]
name = {vm_name}
memory = {memory}
cpus = {cpus}

[disk]
path = {disk_path}
size = {format_bytes(disk_size)}
format = {os.path.splitext(disk_path)[1][1:]}

[display]
type = virtio
graphics = yes

[network]
type = virtio
bridged = no
"""
    
    config_path = f"{vm_name}.vmx"
    with open(config_path, 'w') as f:
        f.write(config)
    
    print(f"   Config: {config_path}")
    return config_path

def main():
    parser = argparse.ArgumentParser(description='VM Creator - Create virtual machines')
    parser.add_argument('name', help='VM name')
    parser.add_argument('--disk-size', '-d', required=True, help='Disk size (e.g., 10G, 512M)')
    parser.add_argument('--format', '-f', choices=FORMATS, default='qcow2', help='Disk format')
    parser.add_argument('--memory', '-m', type=int, default=1024, help='Memory in MB')
    parser.add_argument('--cpus', '-c', type=int, default=1, help='Number of CPUs')
    parser.add_argument('--disk-path', help='Custom disk path')
    
    args = parser.parse_args()
    
    disk_size = parse_size(args.disk_size)
    
    if disk_size < 1024**2:
        print("Error: Disk size must be at least 1 MB")
        sys.exit(1)
    
    # Default disk path
    disk_path = args.disk_path or f"{args.name}.{args.format}"
    
    print("=" * 50)
    print(f"🖥️  Creating VM: {args.name}")
    print("=" * 50)
    
    # Create disk image
    if args.format == 'qcow2':
        create_qcow2(disk_path, disk_size)
    elif args.format == 'raw':
        create_raw(disk_path, disk_size)
    elif args.format == 'vmdk':
        create_vmdk(disk_path, disk_size)
    
    # Create config
    create_vm_config(args.name, disk_path, disk_size, args.memory, args.cpus)
    
    print()
    print("✅ VM created successfully!")
    print()
    print("Next steps:")
    print(f"  1. Install OS: qemu-system-x86_64 -hda {disk_path} -cdrom os.iso -boot d")
    print(f"  2. Run VM: qemu-system-x86_64 -hda {disk_path} -m {args.memory}")

if __name__ == '__main__':
    main()
