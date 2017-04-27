from bitcoin import core
from strategy import Strategy
from strategy import BlockOrigin
from strategy import Action
from strategy import ActionException
from strategies import selfish_mining_strategy
import logging


class Chain:
    def __init__(self, networking):

        self.networking = networking

        genesis_hash = core.CoreRegTestParams.GENESIS_BLOCK.GetHash()

        self.genesis = Block(genesis_hash, None, BlockOrigin.public)
        self.genesis.transfer_allowed = True
        self.tips = [self.genesis]
        self.blocks = {genesis_hash: self.genesis}
        self.orphan_blocks = []
        self.action_service = Strategy(selfish_mining_strategy)

    def process_block(self, block, block_origin):

        if self.try_to_insert_block(block, block_origin):

            fork = self.get_private_public_fork()
            logging.debug('current {}'.format(fork))
            try:
                action = self.action_service.find_action(fork.private_height, fork.public_height, block_origin)

                self.execute_action(action, fork.private_tip, fork.public_tip)
            except ActionException as exception:
                logging.warn(exception.message)

    def execute_action(self, action, private_tip, public_tip):
        blocks_to_transfer = []

        if action is Action.match:
            if public_tip.height > private_tip.height:
                raise ActionException("private tip_height={} must >= then public tip_height={} -"
                                      " match not possible".format(public_tip.height, private_tip.height))

            private_block = private_tip
            while private_block.height > public_tip.height:
                private_block = private_block.prevBlock

            blocks_to_transfer.extend(get_blocks_transfer_unallowed(private_block))
            blocks_to_transfer.extend(get_blocks_transfer_unallowed(public_tip))

        elif action is Action.override:
            if public_tip.height >= private_tip.height:
                raise ActionException("private tip_height={} must > then public tip_height={} -"
                                      " override not possible".format(public_tip.height, private_tip.height))

            private_block = private_tip
            while private_block.height > public_tip.height + 1:
                private_block = private_block.prevBlock

            blocks_to_transfer.extend(get_blocks_transfer_unallowed(private_block))
            blocks_to_transfer.extend(get_blocks_transfer_unallowed(public_tip))

        elif action is Action.adopt:
            if private_tip.height >= public_tip.height:
                raise ActionException("public tip_height={} must > then private tip_height={} -"
                                      " adopt not possible".format(public_tip.height, private_tip.height))
            blocks_to_transfer.extend(get_blocks_transfer_unallowed(public_tip))

        logging.info('there are {} block invs to be send'.format(len(blocks_to_transfer)))
        if len(blocks_to_transfer) > 0:
            for block in blocks_to_transfer:
                block.transfer_allowed = True

            self.networking.send_inv(blocks_to_transfer)

        logging.info('executed action {}'.format(action))

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

        logging.info('{} inserted into chain'.format(block))

    def get_private_public_fork(self):
        highest_private_tip = None
        highest_public_tip = None
        for tip in self.tips:
            if tip.block_origin == BlockOrigin.private:
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


def get_blocks_transfer_unallowed(block):
    blocks = []
    while block.transfer_allowed is False:
        blocks.append(block)

        block = block.prevBlock
    return blocks


class Block:
    def __init__(self, hash, hashPrevBlock, block_origin):
        self.child_blocks = []
        self.hash = hash
        self.hashPrevBlock = hashPrevBlock
        self.prevBlock = None
        self.height = 0
        self.block_origin = block_origin
        self.transfer_allowed = False

    def __repr__(self):
        return 'block(height={} block_origin={})'.format(self.height, self.block_origin)


class Fork:
    def __init__(self, private_tip, public_tip):
        self.private_tip = private_tip
        self.private_height = -1
        self.public_tip = public_tip
        self.public_height = -1

    def __repr__(self):
        return 'fork(private_height={} public_height={})'.format(self.private_height, self.public_height)
