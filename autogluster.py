#!/bin/env python3

from os import path
from glob import glob
import sh

def mountpoint(device):
    """Return gluster-friendly mounting point of a device path."""
    name = path.basename(device)
    split = name.split("-")
    i = split.index("usb")
    mount = path.join("/mnt/usb", split[i+1]).replace(":", "..")
    return mount

# Get available USB drives
drives = glob("/dev/disk/by-path/*-usb-*part1")

# Get intended mount points
mounts = [mountpoint(device) for device in drives]

# Get all previously mounted points
mounted = glob("/mnt/usb/*")

# Local hostname
hostname = sh.hostname("-f").strip()

# Unmount all missing drives
for mount in mounted:
    if mount not in mounts:
        print(f"Unmounting {mount}")
        try:
            sh.umount(mount)
        except Exception as e:
            pass

        try:
            sh.rmdir(mount)
        except Exception as e:
            pass

# Get local brick mount points and remove those that are not present
for volume in sh.gluster.volume.list():
    volume = volume.strip()
    for line in sh.gluster.volume.info(volume):
        if "Brick" in line and "Bricks" not in line:
            host, mount = line.split()[1].strip().split(":")
            if host.lower() == hostname.lower():
                if not path.exists(mount):
                    print(f"Removing brick {host}:{mount} from {volume}")
                    sh.gluster.volume(sh.yes(_piped=True), "remove-brick", volume, f"{host}:{mount}", "force")

# Mount all drives
for drive in drives:
    mount = mountpoint(drive)
    sh.mkdir("-p", mount)
    sh.chmod("go-w", mount)
    print(f"Mounting {drive} to {mount}")
    try:
        sh.mount(drive, mount)
    except Exception:
        pass

# Check drives for ’autogluster’ file and add them to gluster
for drive in drives:
    mount = mountpoint(drive)
    autogluster = path.join(mount, "autogluster")
    if not path.exists(autogluster):
        continue

    with open(autogluster, "rt") as f:
        gluster_volume, brick_path = f.readline().split()

    brick_path = path.join(mount, brick_path).replace(":", "\:")
    glusterfs = path.join(brick_path, ".glusterfs")

    print(glusterfs)
    # Remove possible previous gluster information
    if path.exists(glusterfs):
        sh.rm("-rf", glusterfs)
    try:
        sh.setfattr("-x", "trusted.glusterfs.volume-id", brick_path)
        sh.setfattr("-x", "trusted.gfid", brick_path)
    except Exception:
        pass

    print(f"Adding {brick_path} to {gluster_volume}")
    sh.gluster.volume("add-brick", gluster_volume, f"{hostname}:{brick_path}")
