from bitcoin import core
from strategy import BlockOrigin
from strategy import ActionException
import logging


class Chain:
    def __init__(self, executor, strategy):
        self.executor = executor
        self.strategy = strategy

        genesis_hash = core.CoreRegTestParams.GENESIS_BLOCK.GetHash()

        self.genesis = Block(genesis_hash, None, BlockOrigin.public)
        self.genesis.transfer_allowed = True
        self.tips = [self.genesis]
        self.blocks = {genesis_hash: self.genesis}
        self.orphan_blocks = []

    def process_block(self, block, block_origin):

        fork_before = get_private_public_fork(self.tips)
        logging.debug('fork before {}'.format(fork_before))

        self.try_to_insert_block(block, block_origin)

        fork_after = get_private_public_fork(self.tips)
        logging.debug('fork after {}'.format(fork_after))

        if fork_before != fork_after:
            try:
                action = self.strategy.find_action(fork_after.private_height, fork_after.public_height, block_origin)

                self.executor.execute(action, fork_after.private_tip, fork_after.public_tip)
            except ActionException as exception:
                logging.warn(exception.message)

    def try_to_insert_block(self, received_block, block_origin):
        prevBlock = None
        for tip in self.tips:
            if tip.hash == received_block.hashPrevBlock:
                prevBlock = tip
                break
        if prevBlock is None:
            for block in self.blocks.values():
                if block.hash == received_block.hashPrevBlock:
                    prevBlock = block
                    break

        block = Block(received_block.GetHash(), received_block.hashPrevBlock, block_origin)
        self.blocks[block.hash] = block

        if prevBlock is None:
            self.orphan_blocks.append(block)
            logging.info('{} added to orphan blocks'.format(block))
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
        block.height = prevBlock.height + 1
        block.prevBlock = prevBlock

        logging.info('{} inserted into chain'.format(block))


def get_private_public_fork(tips):
    highest_private_tip = None
    highest_public_tip = None
    for tip in tips:
        if tip.block_origin == BlockOrigin.private and tip.transfer_allowed is False:
            if highest_private_tip is None:
                highest_private_tip = tip
            elif highest_private_tip.height < tip.height:
                highest_private_tip = tip
        else:
            if highest_public_tip is None:
                highest_public_tip = tip
            elif highest_public_tip.height < tip.height:
                highest_public_tip = tip

    fork = Fork(highest_private_tip, highest_public_tip)

    if fork.private_tip is None:
        fork.private_tip = fork.public_tip
        fork.private_height = fork.public_height = 0
        return fork

    fork_point = highest_private_tip
    while fork_point.block_origin is BlockOrigin.private:
        fork_point = fork_point.prevBlock

    if highest_public_tip is None:
        fork.public_tip = fork_point

    fork.private_height = fork.private_tip.height - fork_point.height
    fork.public_height = fork.public_tip.height - fork_point.height
    return fork


class Block:
    def __init__(self, hash, hashPrevBlock, block_origin):
        self.hash = hash
        self.hashPrevBlock = hashPrevBlock
        self.prevBlock = None
        self.height = 0
        self.block_origin = block_origin
        self.transfer_allowed = False

    def __repr__(self):
        return 'block(height={} block_origin={})'.format(self.height, self.block_origin)

    def __eq__(self, other):
        return self.hash == other.hash

    def __ne__(self, other):
        return self.hash != other.hash


class Fork:
    def __init__(self, private_tip, public_tip):
        self.private_tip = private_tip
        self.private_height = -1
        self.public_tip = public_tip
        self.public_height = -1

    def __repr__(self):
        return 'fork(private_height={} public_height={})'.format(self.private_height, self.public_height)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return self.__dict__ != other.__dict__
