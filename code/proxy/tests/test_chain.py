import unittest
from chain import Chain
from mock import MagicMock
from bitcoin import messages
from bitcoin import core
from actionservice import BlockOrigin


class ChainTest(unittest.TestCase):

    def setUp(self):
        self.chain = Chain()
        self.chain.action_service = MagicMock()

    def test_try_to_insert_block(self):
        block = core.CBlock()
        msg = messages.msg_block
        msg.block = block
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        self.assertTrue(block.GetHash() in self.chain.blocks)
        self.assertEqual(len(self.chain.blocks), 2)

    def test_try_to_insert_block_two_times(self):
        block = core.CBlock()
        msg = messages.msg_block
        msg.block = block
        self.chain.try_to_insert_block(msg, BlockOrigin.public)
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        self.assertEqual(len(self.chain.blocks), 2)

    def test_try_to_insert_block(self):
        block = core.CBlock(hashPrevBlock=genesis_hash())
        msg = messages.msg_block
        msg.block = block
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)
        self.assertEqual(self.chain.tips[0].height, 1)

    def test_try_to_insert_two_blocks(self):
        first_block = core.CBlock(hashPrevBlock=genesis_hash())
        msg = messages.msg_block
        msg.block = first_block
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())
        msg.block = second_block
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)
        self.assertEqual(self.chain.tips[0].height, 2)

    def test_try_to_insert_fork(self):
        first_block = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        msg = messages.msg_block
        msg.block = first_block
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        second_block = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)
        msg.block = second_block
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 2)
        self.assertEqual(self.chain.tips[0].height, 1)
        self.assertEqual(self.chain.tips[1].height, 1)

    def test_try_to_insert_orphan_blocks(self):
        first_block = core.CBlock(hashPrevBlock=genesis_hash())
        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())
        msg = messages.msg_block
        msg.block = second_block
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        msg.block = first_block
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)
        self.assertEqual(self.chain.tips[0].height, 2)
        self.assertEqual(self.chain.tips[0].prevBlock.height, 1)

    def test_try_to_insert_two_orphan_blocks(self):
        first_block = core.CBlock(hashPrevBlock=genesis_hash())
        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())
        third_block = core.CBlock(hashPrevBlock=second_block.GetHash())

        msg = messages.msg_block
        msg.block = third_block
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        msg.block = second_block
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        msg.block = first_block
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)
        self.assertEqual(self.chain.tips[0].height, 3)
        self.assertEqual(self.chain.tips[0].prevBlock.height, 2)

    def test_length_of_fork_alice_no_chain(self):
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash())
        second_block_chain_b = core.CBlock(hashPrevBlock=first_block_chain_b.GetHash())

        msg = messages.msg_block
        msg.block = second_block_chain_b
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        msg.block = first_block_chain_b
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)

        length_alice, length_public = self.chain.length_of_fork()
        self.assertEqual(length_alice, 0)
        self.assertEqual(length_public, 0)

    def test_length_of_fork_lead_public(self):
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_b = core.CBlock(hashPrevBlock=first_block_chain_b.GetHash())
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        msg = messages.msg_block
        msg.block = second_block_chain_b
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        msg.block = first_block_chain_b
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        msg.block = first_block_chain_a
        self.chain.try_to_insert_block(msg, BlockOrigin.private)

        length_alice, length_public = self.chain.length_of_fork()
        self.assertEqual(length_alice, 1)
        self.assertEqual(length_public, 2)

    def test_length_of_fork_lead_alice(self):
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_a = core.CBlock(hashPrevBlock=first_block_chain_a.GetHash())
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        msg = messages.msg_block
        msg.block = second_block_chain_a
        self.chain.try_to_insert_block(msg, BlockOrigin.private)

        msg.block = first_block_chain_a
        self.chain.try_to_insert_block(msg, BlockOrigin.private)

        msg.block = first_block_chain_b
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        length_alice, length_public = self.chain.length_of_fork()
        self.assertEqual(length_alice, 2)
        self.assertEqual(length_public, 1)

    def test_length_of_fork_private_fork_point(self):
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_a = core.CBlock(hashPrevBlock=first_block_chain_a.GetHash())
        third_a_block_chain_a = core.CBlock(hashPrevBlock=second_block_chain_a.GetHash(), nNonce=1)
        third_b_block_chain_a = core.CBlock(hashPrevBlock=second_block_chain_a.GetHash(), nNonce=2)
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        msg = messages.msg_block
        msg.block = second_block_chain_a
        self.chain.try_to_insert_block(msg, BlockOrigin.private)

        msg.block = first_block_chain_a
        self.chain.try_to_insert_block(msg, BlockOrigin.private)

        msg.block = third_a_block_chain_a
        self.chain.try_to_insert_block(msg, BlockOrigin.private)

        msg.block = third_b_block_chain_a
        self.chain.try_to_insert_block(msg, BlockOrigin.private)

        msg.block = first_block_chain_b
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 3)

        length_alice, length_public = self.chain.length_of_fork()
        self.assertEqual(length_alice, 3)
        self.assertEqual(length_public, 1)

    def test_length_of_fork_public_fork_point(self):
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_b = core.CBlock(hashPrevBlock=first_block_chain_b.GetHash())
        third_a_block_chain_b = core.CBlock(hashPrevBlock=second_block_chain_b.GetHash(), nNonce=1)
        third_b_block_chain_b = core.CBlock(hashPrevBlock=second_block_chain_b.GetHash(), nNonce=2)
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        msg = messages.msg_block
        msg.block = second_block_chain_b
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        msg.block = first_block_chain_b
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        msg.block = third_a_block_chain_b
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        msg.block = third_b_block_chain_b
        self.chain.try_to_insert_block(msg, BlockOrigin.public)

        msg.block = first_block_chain_a
        self.chain.try_to_insert_block(msg, BlockOrigin.private)

        self.assertEqual(len(self.chain.tips), 3)

        length_alice, length_public = self.chain.length_of_fork()
        self.assertEqual(length_alice, 1)
        self.assertEqual(length_public, 3)

    def test_process_block(self):
        self.chain.try_to_insert_block = MagicMock(return_value=False)
        self.chain.length_of_fork = MagicMock()

        msg = messages.msg_block
        msg.block = None
        self.chain.process_block(msg, BlockOrigin.public)

        self.assertTrue(self.chain.try_to_insert_block.called)
        self.assertFalse(self.chain.length_of_fork.called)
        self.assertFalse(self.chain.action_service.find_action.called)

    def test_process_block(self):
        self.chain.try_to_insert_block = MagicMock(return_value=True)
        self.chain.length_of_fork = MagicMock(return_value=(0, 0))

        msg = messages.msg_block
        msg.block = None
        self.chain.process_block(msg, BlockOrigin.public)

        self.assertTrue(self.chain.try_to_insert_block.called)
        self.assertTrue(self.chain.length_of_fork.called)
        self.assertTrue(self.chain.action_service.find_action.called)



def genesis_hash():
    return core.CoreRegTestParams.GENESIS_BLOCK.GetHash()
