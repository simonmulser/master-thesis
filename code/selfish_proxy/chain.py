from bitcoin import core
from strategy import BlockOrigin
from strategy import ActionException
import logging
import chainutil


class Chain:
    def __init__(self, executor, strategy):
        self.executor = executor
        self.strategy = strategy

        self.tips = [genesis_block]
        self.blocks = {genesis_hash: genesis_block}
        self.orphan_blocks = []

    def process_block(self, block, block_origin):
        logging.info("process Block(hash={}) from {}".format(core.b2lx(block.GetHash()), block_origin))

        fork_before = chainutil.get_private_public_fork(self.tips)
        logging.info('fork before {}'.format(fork_before))

        self.try_to_insert_block(block, block_origin)

        fork_after = chainutil.get_private_public_fork(self.tips)
        logging.info('fork after {}'.format(fork_after))
        logging.debug('fork tip_private={}'.format(core.b2lx(fork_after.private_tip.hash())))
        logging.debug('fork tip_public={}'.format(core.b2lx(fork_after.public_tip.hash())))

        if fork_before != fork_after:
            try:
                action = self.strategy.find_action(fork_after.private_height, fork_after.public_height, block_origin)
                logging.info('found action={}'.format(action))

                self.executor.execute(action, fork_after.private_tip, fork_after.public_tip)
            except ActionException as exception:
                logging.warn(exception.message)
        else:
            logging.debug('the two forks are the same - needs to be taken')

    def try_to_insert_block(self, received_block, block_origin):
        prevBlock = None
        for tip in self.tips:
            if tip.hash() == received_block.hashPrevBlock:
                prevBlock = tip
                break
        if prevBlock is None:
            for block in self.blocks.values():
                if block.hash() == received_block.hashPrevBlock:
                    prevBlock = block
                    break

        block = Block(received_block, block_origin)
        self.blocks[block.hash()] = block

        if prevBlock is None:
            self.orphan_blocks.append(block)
            logging.info('{} added to orphan blocks'.format(block))
        else:
            self.insert_block(prevBlock, block)

            inserted = True
            while inserted:

                inserted_orphan_blocks = []
                for orphan_block in self.orphan_blocks:
                    if block.hash() == orphan_block.hashPrevBlock():
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


class Block:

    def __init__(self, cblock_header, block_origin):
        self.cblock_header = cblock_header
        self.prevBlock = None
        self.cblock = None
        self.height = 0
        self.block_origin = block_origin
        self.transfer_allowed = False
        self.cached_hash = None

    def __repr__(self):
        return '{}(hash={} height={} block_origin={})'\
            .format(self.__class__.__name__, core.b2lx(self.hash()), self.height, self.block_origin)

    def hash_repr(self):
        return 'Block(hash={})' \
            .format(core.b2lx(self.hash()))

    def hash(self):
        if self.cached_hash:
            return self.cached_hash
        else:
            self.cached_hash = self.cblock_header.GetHash()
            return self.cached_hash

    def hashPrevBlock(self):
        return self.cblock_header.hashPrevBlock

    def __eq__(self, other):
        return self.hash() == other.hash()

    def __ne__(self, other):
        return self.hash() != other.hash()

    def __hash__(self):
        return self.hash()

genesis_hash = core.CoreRegTestParams.GENESIS_BLOCK.GetHash()
genesis_block = Block(core.CoreRegTestParams.GENESIS_BLOCK, BlockOrigin.public)
genesis_block.transfer_allowed = True
genesis_block.height = 0
