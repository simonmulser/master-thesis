# Weird behaviour after creation of block

node-2.3 finds block. Afterwards it shares with 7 out of 9 connections they new block. Interestling the node doesn't shares the block with peer 8 and peer 9 which are node 2.1 and node 2.2 in the simulation. These nodes the do not receive the header after 2000ms but only after 4900ms.


*Aggregated simulation log:*
```
...
2017-08-02 20:16:14.280443 node-2.3 UpdateTip: new best=3e4da80e27ebf1193d50b9a8c1d9cc71a5a221b43c5dea373b5cf75ce8d28e8e height=114 version=0x20000000 log2_work=7.8454901 tx=115 date='2017-08-02 20:16:14' progress=1.000000 cache=0.0MiB(114tx)
2017-08-02 20:16:14.288000 simcoin [MainThread  ] [INFO ]  Created block with hash=['3e4da80e27ebf1193d50b9a8c1d9cc71a5a221b43c5dea373b5cf75ce8d28e8e']
2017-08-02 20:16:14.382186 node-2.3 SendMessages: sending header 3e4da80e27ebf1193d50b9a8c1d9cc71a5a221b43c5dea373b5cf75ce8d28e8e to peer=0
2017-08-02 20:16:14.382615 node-2.3 SendMessages: sending header 3e4da80e27ebf1193d50b9a8c1d9cc71a5a221b43c5dea373b5cf75ce8d28e8e to peer=1
2017-08-02 20:16:14.383050 node-2.3 SendMessages: sending header 3e4da80e27ebf1193d50b9a8c1d9cc71a5a221b43c5dea373b5cf75ce8d28e8e to peer=2
2017-08-02 20:16:14.383347 node-2.3 SendMessages: sending header 3e4da80e27ebf1193d50b9a8c1d9cc71a5a221b43c5dea373b5cf75ce8d28e8e to peer=3
2017-08-02 20:16:14.383631 node-2.3 SendMessages: sending header 3e4da80e27ebf1193d50b9a8c1d9cc71a5a221b43c5dea373b5cf75ce8d28e8e to peer=4
2017-08-02 20:16:14.383914 node-2.3 SendMessages: sending header 3e4da80e27ebf1193d50b9a8c1d9cc71a5a221b43c5dea373b5cf75ce8d28e8e to peer=5
2017-08-02 20:16:14.384203 node-2.3 SendMessages: sending header 3e4da80e27ebf1193d50b9a8c1d9cc71a5a221b43c5dea373b5cf75ce8d28e8e to peer=6
2017-08-02 20:16:14.384481 node-2.3 SendMessages: sending header 3e4da80e27ebf1193d50b9a8c1d9cc71a5a221b43c5dea373b5cf75ce8d28e8e to peer=7
2017-08-02 20:16:17.384323 node-1.3 Requesting block 3e4da80e27ebf1193d50b9a8c1d9cc71a5a221b43c5dea373b5cf75ce8d28e8e from  peer=3
2017-08-02 20:16:17.384436 node-1.2 Requesting block 3e4da80e27ebf1193d50b9a8c1d9cc71a5a221b43c5dea373b5cf75ce8d28e8e from  peer=1
2017-08-02 20:16:17.385315 node-1.1 Requesting block 3e4da80e27ebf1193d50b9a8c1d9cc71a5a221b43c5dea373b5cf75ce8d28e8e from  peer=0
2017-08-02 20:16:19.362720 node-2.2 Requesting block 3e4da80e27ebf1193d50b9a8c1d9cc71a5a221b43c5dea373b5cf75ce8d28e8e from  peer=8
2017-08-02 20:16:19.362906 node-2.1 Requesting block 3e4da80e27ebf1193d50b9a8c1d9cc71a5a221b43c5dea373b5cf75ce8d28e8e from  peer=8
...
```

*Peer info from node 2.3:*
```
...
  {
    "id": 8,
    "addr": "240.2.0.1",
...
    "inbound": false,
...
  }, 
  {
    "id": 9,
    "addr": "240.2.0.2",
...
    "inbound": false,
...
  }
]
```

*Nodes.json:*
```
[
    {
        "node_type": "bitcoin",
        "name": "node-1.1",
        "share": 0.2333333333333333,
        "latency": 1000
    },
    ...
    {
        "node_type": "bitcoin",
        "name": "node-2.1",
        "share": 0.09999999999999999,
        "latency": 2000
    },
    {
        "node_type": "bitcoin",
        "name": "node-2.2",
        "share": 0.09999999999999999,
        "latency": 2000
    },
    {
        "node_type": "bitcoin",
        "name": "node-2.3",
        "share": 0.09999999999999999,
        "latency": 2000
    }
]
```