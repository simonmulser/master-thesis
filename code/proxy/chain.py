from bitcoin import core
from actionservice import ActionService
from actionservice import BlockOrigin
from strategy import selfish_mining_strategy


class Chain:

    def __init__(self):

        genesis_hash = core.CoreRegTestParams.GENESIS_BLOCK.GetHash()

        self.genesis = Block(genesis_hash, None, BlockOrigin.public)
        self.tips = [self.genesis]
        self.blocks = [self.genesis]
        self.orphan_blocks = []
        self.known_block_hashes = [genesis_hash]
        self.action_service = ActionService(selfish_mining_strategy)

    def process_block(self, message, visibility):
        received_block = message.block

        if self.try_to_insert_block(received_block, visibility):

            height_private, height_public = self.length_of_fork()

            action = self.action_service.find_action(height_private, height_public, visibility)

            self.execute_action(action)

    def execute_action(self, action):
        pass

    def try_to_insert_block(self, received_block, block_origin):
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

        block = Block(received_block.GetHash(), received_block.hashPrevBlock, block_origin)
        self.blocks.append(block)

        if prevBlock is None:
            self.orphan_blocks.append(block)
            return False
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
            return True

    def insert_block(self, prevBlock, block):
        if prevBlock in self.tips:
            self.tips.remove(prevBlock)
        self.tips.append(block)
        prevBlock.child_blocks.append(block)
        block.height = prevBlock.height + 1
        block.prevBlock = prevBlock

    def length_of_fork(self):
        highest_private_tip = None
        highest_public_tip = None
        for tip in self.tips:
            if tip.visibility == BlockOrigin.private:
                if highest_private_tip is None:
                    highest_private_tip = tip
                elif highest_private_tip.height < tip.height:
                    highest_private_tip = tip
            else:
                if highest_public_tip is None:
                    highest_public_tip = tip
                elif highest_public_tip.height < tip.height:
                    highest_public_tip = tip

        if highest_private_tip is None:
            return 0, 0

        fork_point = highest_private_tip
        while fork_point.visibility is BlockOrigin.private:
            fork_point = fork_point.prevBlock

        if highest_public_tip is None:
            highest_public_tip = fork_point

        return highest_private_tip.height - fork_point.height, highest_public_tip.height - fork_point.height


class Block:

    def __init__(self, hash, hashPrevBlock, visibility):
        self.child_blocks = []
        self.hash = hash
        self.hashPrevBlock = hashPrevBlock
        self.prevBlock = None
        self.height = 0
        self.visibility = visibility
