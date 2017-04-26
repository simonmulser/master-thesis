import unittest
from chain import Chain
from chain import Block
from chain import Fork
from mock import MagicMock
from bitcoin import messages
from bitcoin import core
from actionservice import BlockOrigin


class ChainTest(unittest.TestCase):

    def setUp(self):
        self.chain = Chain()
        self.chain.action_service = MagicMock()

    def test_try_to_insert_block_without_prevHash(self):
        block = core.CBlock()
        self.chain.try_to_insert_block(block, BlockOrigin.public)

        self.assertEqual(len(self.chain.blocks), 2)

    def test_try_to_insert_block_two_times(self):
        block = core.CBlock()
        self.chain.try_to_insert_block(block, BlockOrigin.public)
        self.chain.try_to_insert_block(block, BlockOrigin.public)

        self.assertEqual(len(self.chain.blocks), 2)

    def test_try_to_insert_block(self):
        block = core.CBlock(hashPrevBlock=genesis_hash())
        self.chain.try_to_insert_block(block, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)
        self.assertEqual(self.chain.tips[0].height, 1)

    def test_try_to_insert_two_blocks(self):
        first_block = core.CBlock(hashPrevBlock=genesis_hash())
        self.chain.try_to_insert_block(first_block, BlockOrigin.public)

        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())
        self.chain.try_to_insert_block(second_block, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)
        self.assertEqual(self.chain.tips[0].height, 2)

    def test_try_to_insert_fork(self):
        first_block = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        self.chain.try_to_insert_block(first_block, BlockOrigin.public)

        second_block = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)
        self.chain.try_to_insert_block(second_block, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 2)
        self.assertEqual(self.chain.tips[0].height, 1)
        self.assertEqual(self.chain.tips[1].height, 1)

    def test_try_to_insert_orphan_blocks(self):
        first_block = core.CBlock(hashPrevBlock=genesis_hash())
        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())
        self.chain.try_to_insert_block(second_block, BlockOrigin.public)

        self.chain.try_to_insert_block(first_block, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)
        self.assertEqual(self.chain.tips[0].height, 2)
        self.assertEqual(self.chain.tips[0].prevBlock.height, 1)

    def test_try_to_insert_two_orphan_blocks(self):
        first_block = core.CBlock(hashPrevBlock=genesis_hash())
        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())
        third_block = core.CBlock(hashPrevBlock=second_block.GetHash())

        self.chain.try_to_insert_block(third_block, BlockOrigin.public)
        self.chain.try_to_insert_block(second_block, BlockOrigin.public)
        self.chain.try_to_insert_block(first_block, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)
        self.assertEqual(self.chain.tips[0].height, 3)
        self.assertEqual(self.chain.tips[0].prevBlock.height, 2)

    def test_get_private_public_fork_no_private_tip(self):
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash())
        second_block_chain_b = core.CBlock(hashPrevBlock=first_block_chain_b.GetHash())

        self.chain.try_to_insert_block(second_block_chain_b, BlockOrigin.public)
        self.chain.try_to_insert_block(first_block_chain_b, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)

        fork = self.chain.get_private_public_fork()
        self.assertEqual(fork.private_height, 0)
        self.assertEqual(fork.private_tip.hash, second_block_chain_b.GetHash())

        self.assertEqual(fork.public_height, 0)
        self.assertEqual(fork.public_tip.hash, second_block_chain_b.GetHash())

    def test_get_private_public_fork_lead_public(self):
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_b = core.CBlock(hashPrevBlock=first_block_chain_b.GetHash())
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        self.chain.try_to_insert_block(second_block_chain_b, BlockOrigin.public)
        self.chain.try_to_insert_block(first_block_chain_b, BlockOrigin.public)
        self.chain.try_to_insert_block(first_block_chain_a, BlockOrigin.private)

        fork = self.chain.get_private_public_fork()
        self.assertEqual(fork.private_height, 1)
        self.assertEqual(fork.private_tip.hash, first_block_chain_a.GetHash())

        self.assertEqual(fork.public_height, 2)
        self.assertEqual(fork.public_tip.hash, second_block_chain_b.GetHash())

    def test_get_private_public_fork_lead_alice(self):
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_a = core.CBlock(hashPrevBlock=first_block_chain_a.GetHash())
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        self.chain.try_to_insert_block(second_block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(first_block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(first_block_chain_b, BlockOrigin.public)

        fork = self.chain.get_private_public_fork()

        self.assertEqual(fork.private_height, 2)
        self.assertEqual(fork.private_tip.hash, second_block_chain_a.GetHash())

        self.assertEqual(fork.public_height, 1)
        self.assertEqual(fork.public_tip.hash, first_block_chain_b.GetHash())

    def test_get_private_public_fork_private_fork_point(self):
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_a = core.CBlock(hashPrevBlock=first_block_chain_a.GetHash())
        third_a_block_chain_a = core.CBlock(hashPrevBlock=second_block_chain_a.GetHash(), nNonce=1)
        fourth_block_chain_a = core.CBlock(hashPrevBlock=third_a_block_chain_a.GetHash())
        third_b_block_chain_a = core.CBlock(hashPrevBlock=second_block_chain_a.GetHash(), nNonce=2)
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        self.chain.try_to_insert_block(second_block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(first_block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(third_a_block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(third_b_block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(fourth_block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(first_block_chain_b, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 3)

        fork = self.chain.get_private_public_fork()
        self.assertEqual(fork.private_height, 4)
        self.assertEqual(fork.private_tip.hash, fourth_block_chain_a.GetHash())

        self.assertEqual(fork.public_height, 1)
        self.assertEqual(fork.public_tip.hash, first_block_chain_b.GetHash())

    def test_get_private_public_fork_public_fork_point(self):
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_b = core.CBlock(hashPrevBlock=first_block_chain_b.GetHash())
        third_a_block_chain_b = core.CBlock(hashPrevBlock=second_block_chain_b.GetHash(), nNonce=1)
        third_b_block_chain_b = core.CBlock(hashPrevBlock=second_block_chain_b.GetHash(), nNonce=2)
        fourth_block_chain_b = core.CBlock(hashPrevBlock=third_a_block_chain_b.GetHash())
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        self.chain.try_to_insert_block(second_block_chain_b, BlockOrigin.public)
        self.chain.try_to_insert_block(first_block_chain_b, BlockOrigin.public)
        self.chain.try_to_insert_block(third_a_block_chain_b, BlockOrigin.public)
        self.chain.try_to_insert_block(fourth_block_chain_b, BlockOrigin.public)
        self.chain.try_to_insert_block(third_b_block_chain_b, BlockOrigin.public)
        self.chain.try_to_insert_block(first_block_chain_a, BlockOrigin.private)

        self.assertEqual(len(self.chain.tips), 3)

        fork = self.chain.get_private_public_fork()
        self.assertEqual(fork.private_height, 1)
        self.assertEqual(fork.private_tip.hash, first_block_chain_a.GetHash() )

        self.assertEqual(fork.public_height, 4)
        self.assertEqual(fork.public_tip.hash, fourth_block_chain_b.GetHash())

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
