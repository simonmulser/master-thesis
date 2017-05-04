from bitcoin import core
from chain import Block, BlockOrigin


def genesis_hash():
    return core.CoreRegTestParams.GENESIS_BLOCK.GetHash()

genesis_block = Block(genesis_hash(), None, BlockOrigin.public)
genesis_block.transfer_allowed = True
