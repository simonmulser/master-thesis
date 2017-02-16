# zfs on mac
install OpenZFS for OS X Yosemite and run ZFS on usb-device:

```
$ mount
...
/dev/disk3s1 on /Volumes/OpenZFS on OS X 1.6.1 (hfs, local, nodev, nosuid, read-only, noowners, quarantine, mounted by simon)
...

$ zfs list
no datasets available

sudo zpool create -f zpool-docker /dev/disk4s1

$ mount
...
/dev/disk3s1 on /Volumes/OpenZFS on OS X 1.6.1 (hfs, local, nodev, nosuid, read-only, noowners, quarantine, mounted by simon)
zpool-docker on /Volumes/zpool-docker (zfs, local, journaled)
...

zfs list
NAME           USED  AVAIL  REFER  MOUNTPOINT
zpool-docker  1012K  95.0M   957K  /Volumes/zpool-docker

```
___

create simulated DDT histogramm:
```
$ sudo zdb -S zpool-docker

Simulated DDT histogram:

bucket              allocated                       referenced
______   ______________________________   ______________________________
refcnt   blocks   LSIZE   PSIZE   DSIZE   blocks   LSIZE   PSIZE   DSIZE
------   ------   -----   -----   -----   ------   -----   -----   -----
     1       55   1.74M   1.74M   1.74M       55   1.74M   1.74M   1.74M
     2        2   64.5K   64.5K   64.5K        4    129K    129K    129K
   128        8    769K    769K    769K    1.11K    107M    107M    107M
 Total       65   2.56M   2.56M   2.56M    1.17K    109M    109M    109M

dedup = 42.41, compress = 1.00, copies = 1.00, dedup * compress / copies = 42.41
```

dedup (42.41) shows the deduplication-ratio

check actual deduplication:
```
$ zpool list
NAME           SIZE  ALLOC   FREE  EXPANDSZ   FRAG    CAP  DEDUP  HEALTH  ALTROOT
zpool-docker  29.2G   187M  29.1G         -     0%     0%  16.30x  ONLINE  -
```
___

set and check if deduplication is active:
```
$ zfs get dedup zpool-docker

NAME          PROPERTY  VALUE          SOURCE
zpool-docker  dedup     off            default

$ sudo zfs set dedup=on zpool-docker
```
___

check size of pool
```
$ zfs list
NAME           USED  AVAIL  REFER  MOUNTPOINT
zpool-docker   185M  28.2G   185M  /Volumes/zpool-docker
```
___

[explanation of data-files](https://github.com/bitcoin/bitcoin/blob/master/doc/files.md) in bitcoin client

