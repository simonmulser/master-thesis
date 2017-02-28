# zfs documentation and commands
* can be installed on OS X (OpenZFS) and on linux
* can also be mounted from a usb-stick or a large file

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
create a large file to mount:
```
$ truncate -s 14M /blockchain/simon/local_test_zfs.dat
```
___

print DDT (deduplication table) of pool:
```
$ sudo zdb -DD zpool-docker
DDT-sha256-zap-duplicate: 183 entries, size 318 on disk, 201 in core
DDT-sha256-zap-unique: 10182 entries, size 276 on disk, 156 in core

DDT histogram (aggregated over all DDTs):

bucket              allocated                       referenced
______   ______________________________   ______________________________
refcnt   blocks   LSIZE   PSIZE   DSIZE   blocks   LSIZE   PSIZE   DSIZE
------   ------   -----   -----   -----   ------   -----   -----   -----
     1    9.94K   4.97M   4.97M   4.97M    9.94K   4.97M   4.97M   4.97M
     2        7   3.50K   3.50K   3.50K       20     10K     10K     10K
     4       27   13.5K   13.5K   13.5K      124     62K     62K     62K
     8      146     73K     73K     73K    1.42K    730K    730K    730K
    16        2      1K      1K      1K       40     20K     20K     20K
  256K        1     512     512     512     339K    169M    169M    169M
 Total    10.1K   5.06M   5.06M   5.06M     350K    175M    175M    175M

dedup = 34.60, compress = 1.00, copies = 1.00, dedup * compress / copies = 34.60
```

dedup (34.50) shows the deduplication-ratio

print size and deduplication of pool in a more compact format:
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

check size of dataset:
```
$ zfs list
NAME           USED  AVAIL  REFER  MOUNTPOINT
zpool-docker   185M  28.2G   185M  /Volumes/zpool-docker
```
___

[explanation of data-files](https://github.com/bitcoin/bitcoin/blob/master/doc/files.md) in bitcoin client
___

[install bitcoin](https://github.com/bitcoin/bitcoin/blob/master/doc/build-osx.md) but as project location in Qt use `src` instead of `src/qt`

start `bitcoind -regtest` executable in `src` from Qt Creator IDE

set breakpoints in client to see how the client writes data:
* mining.cpp::generate
* validation.cpp:AcceptBlock
* validation.cpp:WriteBlockToDisk

run `bitcoin-cli -regtest generate 1` in `src` from the terminal to generate a block
___

`man zfs` about deduplication and recordsize
```
dedup=on | off | verify | sha256[,verify] | sha512[,verify] | skein[,verify]
    Configures deduplication for a  dataset. The default value is off.
    The default deduplication checksum is sha256 (this may change in the
    future).  When dedup is enabled, the checksum defined here overrides
    the checksum property. Setting the value to verify has the same
    effect as the setting sha256,verify.
    If set to verify, ZFS will do a byte-to-byte comparsion in case of
    two blocks having the same signature to make sure the block contents
    are identical.

recordsize=size
    Specifies a suggested block size for files in the file system. This
    property is designed solely for use with database workloads that
    access files in fixed-size records.  ZFS automatically tunes block
    sizes according to internal algorithms optimized for typical access
    patterns.

    For databases that create very large files but access them in small
    random chunks, these algorithms may be suboptimal. Specifying a
    recordsize greater than or equal to the record size of the database
    can result in significant performance gains. Use of this property for
    general purpose file systems is strongly discouraged, and may
    adversely affect performance.

    The size specified must be a power of two greater than or equal to
    512 and less than or equal to 128 Kbytes.  If the large_blocks fea-
    ture is enabled on the pool, the size may be up to 1 Mbyte.  See
    zpool-features(7) for details on ZFS feature flags.

    Changing the file system's recordsize affects only files created
    afterward; existing files are unaffected.

    This property can also be referred to by its shortened column name,
    recsize.
```
zfs blocks cannot be smaller then 512 bytes whereas a bitcoin block can be smaller then 512 bytes

therefore we set the recordsize to 512 bytes

```
$ zfs get recordsize zpool-docker
NAME          PROPERTY    VALUE    SOURCE
zpool-docker  recordsize  128K     default

$ sudo zfs set recordsize=512b zpool-docker
```
___

patch client in validation.cpp

```
        unsigned int nextPowerOfTwoExponent = ceil(log2(nBlockSize + 8));
        unsigned int nextPowerOfTwo = nextPowerOfTwoExponent > 9? pow(2, nextPowerOfTwoExponent) : pow(2,9);
        nBlockSize = nextPowerOfTwo - 8;
```
___

simulation on VM of sba-research
* run current simcoin implementation with 10 nodes and 210blocks
* check DDT if everything makes sense

```
$ du -h btn-0/
176K    btn-0/regtest/database
20K btn-0/regtest/chainstate
64K btn-0/regtest/blocks/index
18M btn-0/regtest/blocks
20M btn-0/regtest
20M btn-0/
```

```
$ sudo zdb -DD zpool-docker
DDT-sha256-zap-duplicate: 183 entries, size 318 on disk, 201 in core
DDT-sha256-zap-unique: 10182 entries, size 276 on disk, 156 in core

DDT histogram (aggregated over all DDTs):

bucket              allocated                       referenced
______   ______________________________   ______________________________
refcnt   blocks   LSIZE   PSIZE   DSIZE   blocks   LSIZE   PSIZE   DSIZE
------   ------   -----   -----   -----   ------   -----   -----   -----
     1    9.94K   4.97M   4.97M   4.97M    9.94K   4.97M   4.97M   4.97M
     2        7   3.50K   3.50K   3.50K       20     10K     10K     10K
     4       27   13.5K   13.5K   13.5K      124     62K     62K     62K
     8      146     73K     73K     73K    1.42K    730K    730K    730K
    16        2      1K      1K      1K       40     20K     20K     20K
  256K        1     512     512     512     339K    169M    169M    169M
 Total    10.1K   5.06M   5.06M   5.06M     350K    175M    175M    175M

dedup = 34.60, compress = 1.00, copies = 1.00, dedup * compress / copies = 34.60

```
we can see:
* recordsize=512bytes worked (350K*512=127M)
* 9.94K blocks with a total size of 4.97M are not deduplicated
* 146 blocks are referenced more than 8 times - these blocks should be bitcoin blocks

* 1 block is 339K time referenced what makes a 175M. This sould be a totally empty block (everything 0) which is caused by the blk***.dat file because in this file the rest of the space is filled up with zeros and the file has a size of 16M.

___

consider to increase blocksize to 1K or 2K because in a normal simulation blocks are not empty and therefore bigger.
