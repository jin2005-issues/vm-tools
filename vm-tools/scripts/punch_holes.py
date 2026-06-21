#!/usr/bin/env python3
"""
VM Hole Puncher - Punch holes in sparse disk images

Usage:
    python3 punch_holes.py <image_file> [--format qcow2|raw|vmdk] [--analyze]
"""

import os
import sys
import ctypes
import struct
import argparse
from pathlib import Path

# Fallocate flags (Linux)
FALLOC_FL_PUNCH_HOLE = 0x04
FALLOC_FL_KEEP_SIZE = 0x01

# QCOW2 Constants
QCOW_MAGIC = 0x514649FB

def format_bytes(size):
    """Format bytes to human readable"""
    if size < 0:
        return f"-{format_bytes(-size)}"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size) < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def read_qcow2_info(filepath):
    """Read QCOW2 image information"""
    with open(filepath, 'rb') as f:
        header = f.read(128)
        
        magic = struct.unpack('>I', header[0:4])[0]
        if magic != QCOW_MAGIC:
            raise ValueError(f"Invalid QCOW magic: 0x{magic:08X}")
        
        version = struct.unpack('>I', header[4:8])[0]
        backing_offset = struct.unpack('>Q', header[8:16])[0]
        l2_size = struct.unpack('>I', header[16:20])[0]
        cluster_bits = struct.unpack('>I', header[20:24])[0]
        cluster_size_raw = struct.unpack('>I', header[24:28])[0]
        page_size = struct.unpack('>I', header[28:32])[0]
        
        # Virtual size is at offset 24 for v3 format
        virtual_size = struct.unpack('>Q', header[24:32])[0]
        if virtual_size < 1024:
            virtual_size = struct.unpack('>Q', header[32:40])[0]
        
        if version == 3:
            l1_offset = struct.unpack('>Q', header[40:48])[0]
            refcount_offset = struct.unpack('>Q', header[48:56])[0]
        else:
            l1_offset = struct.unpack('>Q', header[24:32])[0]
            refcount_offset = struct.unpack('>Q', header[32:40])[0]
        
        cluster_size = cluster_size_raw if cluster_size_raw > 0 else (1 << cluster_bits)
        
        file_size = os.stat(filepath).st_size
        total_clusters = virtual_size // cluster_size if cluster_size > 0 else 0
        
        return {
            'version': version,
            'virtual_size': virtual_size,
            'file_size': file_size,
            'cluster_size': cluster_size,
            'total_clusters': total_clusters,
            'l1_offset': l1_offset,
            'refcount_offset': refcount_offset,
            'backing_offset': backing_offset
        }

def find_data_start(info):
    """Calculate where actual data clusters start"""
    # Metadata area: header + refcount table + L1 + L2 tables
    cs = info['cluster_size']
    tc = info['total_clusters']
    
    # Refcount table (1 cluster)
    refcount_size = cs
    
    # L2 tables: total_clusters / entries_per_l2
    entries_per_l2 = cs // 8
    num_l2_tables = (tc + entries_per_l2 - 1) // entries_per_l2
    l2_size = num_l2_tables * cs
    
    # L1 table (small)
    l1_size = 32
    
    # Data starts after all metadata
    data_start = refcount_size + l2_size + l1_size
    return (data_start // cs + 1) * cs  # Align to cluster

def analyze_image(filepath, image_format='qcow2'):
    """Analyze disk image"""
    print(f"📊 Analyzing {image_format.upper()} image...")
    print("=" * 50)
    
    if image_format == 'qcow2':
        info = read_qcow2_info(filepath)
        
        print(f"File:        {filepath}")
        print(f"Version:     QCOW{info['version']}")
        print(f"Virtual:     {format_bytes(info['virtual_size'])}")
        print(f"File Size:   {format_bytes(info['file_size'])}")
        print(f"Cluster:     {info['cluster_size']:,} bytes")
        print(f"Clusters:    {info['total_clusters']:,}")
        print(f"Compression: {info['file_size'] / info['virtual_size'] * 100:.4f}%")
        print()
        
        data_start = find_data_start(info)
        print(f"Metadata ends: {format_bytes(data_start)}")
        print(f"Data area:     ~{format_bytes(info['virtual_size'] - data_start)}")
        
        savings = info['virtual_size'] - info['file_size']
        if info['file_size'] < info['virtual_size'] * 0.1:
            print("\n✅ Image is already highly sparse")
        else:
            print(f"\n📉 Potential savings: ~{format_bytes(savings)}")
        
    else:  # raw
        file_size = os.stat(filepath).st_size
        print(f"File:      {filepath}")
        print(f"Size:      {format_bytes(file_size)}")
        print(f"Clusters:  {file_size // 4096:,} (4KB blocks)")
        
        # Count zero blocks
        with open(filepath, 'rb') as f:
            zero_blocks = 0
            total_blocks = file_size // 4096
            for i in range(total_blocks):
                data = f.read(4096)
                if all(b == 0 for b in data):
                    zero_blocks += 1
                if i % 10000 == 0 and i > 0:
                    print(f"\r  Scanning: {i/total_blocks*100:.1f}%", end='', flush=True)
            print()
        
        zero_bytes = zero_blocks * 4096
        print(f"\nZero blocks: {zero_blocks:,} / {total_blocks:,}")
        print(f"Zero data:   {format_bytes(zero_bytes)}")
        print(f"Potential:    {format_bytes(zero_bytes)}")

def punch_holes(filepath, image_format='qcow2'):
    """Punch holes in zero clusters"""
    print(f"🔨 Punching holes in {image_format.upper()} image...")
    print("=" * 50)
    
    # Check fallocate
    try:
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        has_fallocate = hasattr(libc, 'fallocate')
    except:
        has_fallocate = False
    
    if not has_fallocate:
        print("⚠️  fallocate not available on this system")
        print("   Holes cannot be punched without kernel support")
        return
    
    if image_format == 'qcow2':
        info = read_qcow2_info(filepath)
        cluster_size = info['cluster_size']
        total_clusters = info['total_clusters']
        data_start = find_data_start(info)
        
        print(f"Cluster size: {format_bytes(cluster_size)}")
        print(f"Data starts:  {format_bytes(data_start)}")
        
    else:  # raw
        file_size = os.stat(filepath).st_size
        cluster_size = 4096
        total_clusters = file_size // cluster_size
        data_start = 0
    
    initial_size = os.stat(filepath).st_size
    zero_clusters = 0
    bytes_punched = 0
    
    with open(filepath, 'r+b') as f:
        for i in range(total_clusters):
            offset = i * cluster_size
            
            if offset < data_start:
                continue
            
            # Check if zero
            f.seek(offset)
            data = f.read(min(4096, cluster_size))
            
            if data and all(b == 0 for b in data):
                zero_clusters += 1
                
                try:
                    result = libc.fallocate(
                        f.fileno(),
                        FALLOC_FL_PUNCH_HOLE | FALLOC_FL_KEEP_SIZE,
                        offset,
                        cluster_size
                    )
                    if result == 0:
                        bytes_punched += cluster_size
                except:
                    pass
            
            if i % 5000 == 0 and i > 0:
                pct = i / total_clusters * 100
                print(f"\r  {pct:6.1f}% | Zero: {zero_clusters:,} | Punched: {format_bytes(bytes_punched)}   ", end='', flush=True)
    
    print()
    print()
    
    final_size = os.stat(filepath).st_size
    actual_saved = initial_size - final_size
    
    print("✅ Complete!")
    print("=" * 50)
    print(f"Zero clusters:  {zero_clusters:,}")
    print(f"Bytes punched: {format_bytes(bytes_punched)}")
    print(f"Before:       {format_bytes(initial_size)}")
    print(f"After:        {format_bytes(final_size)}")
    print(f"Saved:        {format_bytes(max(0, actual_saved))}")
    
    if actual_saved > 0:
        print(f"\n🎉 Saved {format_bytes(actual_saved)}!")
    elif bytes_punched > 0:
        print("\nℹ️  Holes punched (filesystem may not report size change)")
    else:
        print("\nℹ️  No zero clusters found or not supported")

def main():
    parser = argparse.ArgumentParser(description='VM Image Hole Puncher')
    parser.add_argument('file', help='Disk image file')
    parser.add_argument('--format', '-f', choices=['qcow2', 'raw', 'vmdk'], default='qcow2', help='Image format')
    parser.add_argument('--punch', '-p', action='store_true', help='Punch holes (default is analyze only)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)
    
    try:
        if args.punch:
            punch_holes(args.file, args.format)
        else:
            analyze_image(args.file, args.format)
            print("\nRun with --punch to reclaim space")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
