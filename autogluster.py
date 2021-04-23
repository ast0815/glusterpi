#!/bin/env python3

from os import path
from glob import glob
import sh


def mountpoint(device):
    """Return gluster-friendly mounting point of a device path."""
    name = path.basename(device)
    split = name.split("-")
    i = split.index("usb")
    mount = path.join("/mnt/usb", split[i + 1]).replace(":", "..")
    return mount


# Get available USB drives
drives = glob("/dev/disk/by-path/*-usb-*part1")

# Get intended mount points
mounts = [mountpoint(device) for device in drives]

# Get all previously mounted points
mounted = glob("/mnt/usb/*")

# Get ro mounts
ro = []
for line in sh.mount(_iter=True):
    for mount in mounted:
        if mount in line and "ro" in line:
            ro.append(mount)

# Unmount all missing drives
for mount in mounted:
    if mount not in mounts or mount in ro:
        print(f"Unmounting {mount}")
        try:
            sh.umount(mount)
        except Exception as e:
            pass

    try:
        sh.rmdir(mount)
    except Exception as e:
        pass

# Mount all present drives
for drive in drives:
    mount = mountpoint(drive)
    # Abort if folder already exists
    if path.exists(mount):
        print(f"{mount} already exists!")
        continue
    sh.mkdir("-p", mount)
    sh.chmod("go-w", mount)
    print(f"Mounting {drive} to {mount}")
    try:
        sh.mount("-o", "errors=continue", drive, mount)
    except Exception:
        pass

# Restart the gluster processes
print(f"Starting gluster bricks")
try:
    sh.gluster.volume.start("gvol1", "force")
except Exception as e:
    print(e.stderr)
    for word in e.stderr.split():
        for mount in mounted:
            if mount in str(word):
                print(f"Unmounting {mount}")
                sh.umount(mount)
