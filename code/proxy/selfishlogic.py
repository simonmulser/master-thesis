import logging
from bitcoin import net
from bitcoin import messages
from bitcoin import core


class SelfishLogic:

    def __init__(self):

        genesis_hash = core.CoreRegTestParams.GENESIS_BLOCK.GetHash()

        self.genesis = Block(genesis_hash, None)
        self.tips = [self.genesis]
        self.blocks = [self.genesis]
        self.orphan_blocks = []
        self.known_block_hashes = [genesis_hash]

        logging.debug("new selfish proxy")

    def process_inv_msg(self, connection, message):
        relay_inv = []
        for inv in message.inv:
            try:
                if net.CInv.typemap[inv.type] == "Error" or net.CInv.typemap[inv.type] == "TX":
                    relay_inv.append(inv)
                elif net.CInv.typemap[inv.type] == "Block":
                    data_packet = messages.msg_getdata()
                    data_packet.inv.append(message.inv[0])
                    connection.send('getdata', data_packet)
                elif net.CInv.typemap[inv.type] == "FilteredBlock":
                    logging.debug("we dont care about filtered blocks")
                else:
                    logging.debug("unknown inv type")
            except KeyError:
                logging.warn("unknown inv type")

    def process_block(self, connection, message):
        received_block = message.block

        if received_block.GetHash() in self.known_block_hashes:
            return

        parent_block = None
        for tip in self.tips:
            if tip.block_hash == received_block.hashPrevBlock:
                parent_block = tip
                break
        if parent_block is None:
            for block in self.blocks:
                if block.block_hash == received_block.hashPrevBlock:
                    parent_block = block
                    break

        block = Block(received_block.GetHash(), parent_block)
        self.blocks.append(block)

        if parent_block is None:
            self.orphan_blocks.append(block)
        else:
            if parent_block in self.tips:
                self.tips.remove(parent_block)
            self.tips.append(block)
            parent_block.child_blocks.append(block)


class Block:

    def __init__(self, block_hash, parent):
        self.child_blocks = []
        self.block_hash = block_hash
        self.parent = parent
        self.height = parent.height + 1 if parent is not None else 0
