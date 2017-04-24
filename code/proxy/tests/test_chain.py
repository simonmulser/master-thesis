import unittest
from chain import Chain
from bitcoin import messages
from bitcoin import core
from chain import Visibility
import logging


class ChainTest(unittest.TestCase):

    def test_process_block(self):
        logic = Chain()
        block = core.CBlock()
        msg = messages.msg_block
        msg.block = block
        logic.process_block(msg, Visibility.public)

        self.assertTrue(block.GetHash() in logic.blocks)
        self.assertEqual(len(logic.blocks), 2)

    def test_process_block_two_times(self):
        logic = Chain()
        block = core.CBlock()
        msg = messages.msg_block
        msg.block = block
        logic.process_block(msg, Visibility.public)
        logic.process_block(msg, Visibility.public)

        self.assertEqual(len(logic.blocks), 2)

    def test_process_block(self):
        logic = Chain()
        block = core.CBlock(hashPrevBlock=genesis_hash())
        msg = messages.msg_block
        msg.block = block
        logic.process_block(msg, Visibility.public)

        self.assertEqual( len(logic.tips), 1)
        self.assertEqual( logic.tips[0].height, 1)

    def test_process_two_block(self):
        logic = Chain()
        first_block = core.CBlock(hashPrevBlock=genesis_hash())
        msg = messages.msg_block
        msg.block = first_block
        logic.process_block(msg, Visibility.public)

        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())
        msg.block = second_block
        logic.process_block(msg, Visibility.public)

        self.assertEqual(len(logic.tips), 1)
        self.assertEqual(logic.tips[0].height, 2)

    def test_process_fork(self):
        logic = Chain()
        first_block = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        msg = messages.msg_block
        msg.block = first_block
        logic.process_block(msg, Visibility.public)

        second_block = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)
        msg.block = second_block
        logic.process_block(msg, Visibility.public)

        self.assertEqual(len(logic.tips), 2)
        self.assertEqual(logic.tips[0].height, 1)
        self.assertEqual(logic.tips[1].height, 1)

    def test_process_orphan_blocks(self):
        logic = Chain()
        first_block = core.CBlock(hashPrevBlock=genesis_hash())
        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())
        msg = messages.msg_block
        msg.block = second_block
        logic.process_block(msg, Visibility.public)

        msg.block = first_block
        logic.process_block(msg, Visibility.public)

        self.assertEqual(len(logic.tips), 1)
        self.assertEqual(logic.tips[0].height, 2)
        self.assertEqual(logic.tips[0].prevBlock.height, 1)

    def test_process_two_orphan_blocks(self):
        logic = Chain()
        first_block = core.CBlock(hashPrevBlock=genesis_hash())
        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())
        third_block = core.CBlock(hashPrevBlock=second_block.GetHash())

        msg = messages.msg_block
        msg.block = third_block
        logic.process_block(msg, Visibility.public)

        msg.block = second_block
        logic.process_block(msg, Visibility.public)

        msg.block = first_block
        logic.process_block(msg, Visibility.public)

        self.assertEqual(len(logic.tips), 1)
        self.assertEqual(logic.tips[0].height, 3)
        self.assertEqual(logic.tips[0].prevBlock.height, 2)

    def test_length_of_fork_alice_no_chain(self):
        logic = Chain()
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash())
        second_block_chain_b = core.CBlock(hashPrevBlock=first_block_chain_b.GetHash())

        msg = messages.msg_block
        msg.block = second_block_chain_b
        logic.process_block(msg, Visibility.public)

        msg.block = first_block_chain_b
        logic.process_block(msg, Visibility.public)

        self.assertEqual(len(logic.tips), 1)

        length_alice, length_public = logic.length_of_fork()
        self.assertEqual(length_alice, 0)
        self.assertEqual(length_public, 0)

    def test_length_of_fork_lead_public(self):
        chain = Chain()
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_b = core.CBlock(hashPrevBlock=first_block_chain_b.GetHash())
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        msg = messages.msg_block
        msg.block = second_block_chain_b
        chain.process_block(msg, Visibility.public)

        msg.block = first_block_chain_b
        chain.process_block(msg, Visibility.public)

        msg.block = first_block_chain_a
        chain.process_block(msg, Visibility.alice)

        length_alice, length_public = chain.length_of_fork()
        self.assertEqual(length_alice, 1)
        self.assertEqual(length_public, 2)

    def test_length_of_fork_lead_alice(self):
        chain = Chain()
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_a = core.CBlock(hashPrevBlock=first_block_chain_a.GetHash())
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        msg = messages.msg_block
        msg.block = second_block_chain_a
        chain.process_block(msg, Visibility.alice)

        msg.block = first_block_chain_a
        chain.process_block(msg, Visibility.alice)

        msg.block = first_block_chain_b
        chain.process_block(msg, Visibility.public)

        length_alice, length_public = chain.length_of_fork()
        self.assertEqual(length_alice, 2)
        self.assertEqual(length_public, 1)

    def test_length_of_fork_private_fork_point(self):
        chain = Chain()
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_a = core.CBlock(hashPrevBlock=first_block_chain_a.GetHash())
        third_a_block_chain_a = core.CBlock(hashPrevBlock=second_block_chain_a.GetHash(), nNonce=1)
        third_b_block_chain_a = core.CBlock(hashPrevBlock=second_block_chain_a.GetHash(), nNonce=2)
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        msg = messages.msg_block
        msg.block = second_block_chain_a
        chain.process_block(msg, Visibility.alice)

        msg.block = first_block_chain_a
        chain.process_block(msg, Visibility.alice)

        msg.block = third_a_block_chain_a
        chain.process_block(msg, Visibility.alice)

        msg.block = third_b_block_chain_a
        chain.process_block(msg, Visibility.alice)

        msg.block = first_block_chain_b
        chain.process_block(msg, Visibility.public)

        self.assertEqual(len(chain.tips), 3)

        length_alice, length_public = chain.length_of_fork()
        self.assertEqual(length_alice, 3)
        self.assertEqual(length_public, 1)

    def test_length_of_fork_public_fork_point(self):
        chain = Chain()
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_b = core.CBlock(hashPrevBlock=first_block_chain_b.GetHash())
        third_a_block_chain_b = core.CBlock(hashPrevBlock=second_block_chain_b.GetHash(), nNonce=1)
        third_b_block_chain_b = core.CBlock(hashPrevBlock=second_block_chain_b.GetHash(), nNonce=2)
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        msg = messages.msg_block
        msg.block = second_block_chain_b
        chain.process_block(msg, Visibility.public)

        msg.block = first_block_chain_b
        chain.process_block(msg, Visibility.public)

        msg.block = third_a_block_chain_b
        chain.process_block(msg, Visibility.public)

        msg.block = third_b_block_chain_b
        chain.process_block(msg, Visibility.public)

        msg.block = first_block_chain_a
        chain.process_block(msg, Visibility.alice)

        self.assertEqual(len(chain.tips), 3)

        length_alice, length_public = chain.length_of_fork()
        self.assertEqual(length_alice, 1)
        self.assertEqual(length_public, 3)


def genesis_hash():
    return core.CoreRegTestParams.GENESIS_BLOCK.GetHash()
