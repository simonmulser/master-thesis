from bitcoin import core
from strategy import BlockOrigin
from strategy import ActionException
import strategy
import logging


class Chain:
    def __init__(self, executor, strategy):
        self.executor = executor
        self.strategy = strategy

        self.tips = [genesis_block]
        self.blocks = {genesis_hash: genesis_block}
        self.orphan_blocks = []

    def process_block(self, block, block_origin):
        logging.info("process Block(hash={}) from {}".format(core.b2lx(block.GetHash()), block_origin))

        fork_before = get_private_public_fork(self.tips)
        logging.info('fork before {}'.format(fork_before))

        self.try_to_insert_block(block, block_origin)

        fork_after = get_private_public_fork(self.tips)
        logging.info('fork after {}'.format(fork_after))
        logging.debug('fork tip_private={}'.format(core.b2lx(fork_after.private_tip.hash)))
        logging.debug('fork tip_public={}'.format(core.b2lx(fork_after.public_tip.hash)))

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
    highest_private = get_highest_block(tips, BlockOrigin.private)
    highest_public = get_highest_block(tips, BlockOrigin.public)

    high_tip, low_tip = (highest_private, highest_public) \
        if highest_private.height > highest_public.height else (highest_public, highest_private)

    while high_tip.height > low_tip.height:
        high_tip = high_tip.prevBlock

    while high_tip is not low_tip:
        high_tip = high_tip.prevBlock
        low_tip = low_tip.prevBlock

    fork_height = high_tip.height
    return Fork(highest_private, highest_private.height - fork_height,
                highest_public, highest_public.height - fork_height)


def get_highest_block(tips, block_origin):
    highest_block = genesis_block

    for tip in tips:
        if tip.block_origin is block_origin:
            if highest_block.height <= tip.height:
                highest_block = tip
        elif tip.transfer_allowed is True:
            if highest_block.height < tip.height:
                highest_block = tip
        else:
            tmp = tip
            while strategy.opposite_origin(tmp.block_origin) is block_origin and tmp.transfer_allowed is False:
                tmp = tmp.prevBlock
            if highest_block.height < tmp.height:
                highest_block = tmp
    return highest_block


def get_relevant_tips(tips):
    highest_tip = max(tips, key=lambda t: t.height)
    return [tip for tip in tips if tip.height > highest_tip.height - 10]


class Block:
    def __init__(self, block_hash, hashPrevBlock, block_origin):
        self.hash = block_hash
        self.hashPrevBlock = hashPrevBlock
        self.prevBlock = None
        self.height = 0
        self.block_origin = block_origin
        self.transfer_allowed = False

    def __repr__(self):
        return '{}(hash={} height={} block_origin={})'\
            .format(self.__class__.__name__, core.b2lx(self.hash), self.height, self.block_origin)

    def hash_repr(self):
        return 'Block(hash={})' \
            .format(core.b2lx(self.hash))

    def __eq__(self, other):
        return self.hash == other.hash

    def __ne__(self, other):
        return self.hash != other.hash

    def __hash__(self):
        return hash(self.hash)


class Fork:
    def __init__(self, private_tip, private_height, public_tip, public_height):
        self.private_tip = private_tip
        self.private_height = private_height
        self.public_tip = public_tip
        self.public_height = public_height

    def __repr__(self):
        return '{}(private_height={} public_height={})'.format(self.__class__.__name__, self.private_height, self.public_height)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return self.__dict__ != other.__dict__

genesis_hash = core.CoreRegTestParams.GENESIS_BLOCK.GetHash()
genesis_block = Block(genesis_hash, None, BlockOrigin.public)
genesis_block.transfer_allowed = True
genesis_block.height = 0
