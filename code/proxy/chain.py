import logging
from bitcoin import core


class Chain:

    def __init__(self):

        genesis_hash = core.CoreRegTestParams.GENESIS_BLOCK.GetHash()

        self.genesis = Block(genesis_hash, None)
        self.tips = [self.genesis]
        self.blocks = [self.genesis]
        self.orphan_blocks = []
        self.known_block_hashes = [genesis_hash]

        logging.debug("new selfish proxy")

    def process_block(self, message):
        received_block = message.block

        if received_block.GetHash() in self.known_block_hashes:
            return
        else:
            self.known_block_hashes.append(received_block.GetHash())

        prevBlock = None
        for tip in self.tips:
            if tip.hash == received_block.hashPrevBlock:
                prevBlock = tip
                break
        if prevBlock is None:
            for block in self.blocks:
                if block.hash == received_block.hashPrevBlock:
                    prevBlock = block
                    break

        block = Block(received_block.GetHash(), received_block.hashPrevBlock)
        self.blocks.append(block)

        if prevBlock is None:
            self.orphan_blocks.append(block)
        else:
            self.insert_block(prevBlock, block)

            inserted = True
            while inserted:

                inserted_orphan_blocks = []
                for orphan_block in self.orphan_blocks:
                    if block.hash == orphan_block.hashPrevBlock:
                        self.insert_block(block, orphan_block)
                        inserted_orphan_blocks.append(orphan_block)
                        block = orphan_block

                if len(inserted_orphan_blocks) == 0:
                    inserted = False

                for inserted_orphan_block in inserted_orphan_blocks:
                    if inserted_orphan_block in self.orphan_blocks:
                        self.orphan_blocks.remove(inserted_orphan_block)

    def insert_block(self, prevBlock, block):
            if prevBlock in self.tips:
                self.tips.remove(prevBlock)
            self.tips.append(block)
            prevBlock.child_blocks.append(block)
            block.height = prevBlock.height + 1
            block.prevBlock = prevBlock

    def chain_length(self):
        max_length = 0
        for tip in self.tips:
            if tip.height > max_length:
                max_length = tip.height
        return max_length


class Block:

    def __init__(self, hash, hashPrevBlock):
        self.child_blocks = []
        self.hash = hash
        self.hashPrevBlock = hashPrevBlock
        self.prevBlock = None
        self.height = 0
