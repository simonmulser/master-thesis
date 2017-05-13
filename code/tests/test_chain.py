import unittest
from chain import Chain
from chain import Block
from chain import Fork
import chain
from mock import MagicMock
from mock import patch
from bitcoin import core
from strategy import BlockOrigin
from strategy import ActionException


class ChainTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(ChainTest, self).__init__(*args, **kwargs)

        self.executor = None
        self.strategy = None
        self.chain = None
        self.first_block_chain_a = None
        self.second_block_chain_a = None
        self.first_block_chain_b = None
        self.second_block_chain_b = None

    def setUp(self):
        self.executor = MagicMock()
        self.strategy = MagicMock()
        self.chain = Chain(self.executor, self.strategy)
        self.chain.strategy = MagicMock()

        self.first_block_chain_b = Block('1b', '0', BlockOrigin.public)
        self.first_block_chain_b.height = 1
        self.first_block_chain_b.prevBlock = chain.genesis_block

        self.second_block_chain_b = Block('2b', '1b', BlockOrigin.public)
        self.second_block_chain_b.height = 2
        self.second_block_chain_b.prevBlock = self.first_block_chain_b

        self.first_block_chain_a = Block('1a', '0', BlockOrigin.private)
        self.first_block_chain_a.height = 1
        self.first_block_chain_a.prevBlock = chain.genesis_block

        self.second_block_chain_a = Block('2a', '1a', BlockOrigin.private)
        self.second_block_chain_a.height = 2
        self.second_block_chain_a.prevBlock = self.first_block_chain_a

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
        block = core.CBlock(hashPrevBlock=chain.genesis_hash)
        self.chain.try_to_insert_block(block, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)
        self.assertEqual(self.chain.tips[0].height, 1)

    def test_try_to_insert_two_blocks(self):
        first_block = core.CBlock(hashPrevBlock=chain.genesis_hash)
        self.chain.try_to_insert_block(first_block, BlockOrigin.public)

        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())
        self.chain.try_to_insert_block(second_block, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)
        self.assertEqual(self.chain.tips[0].height, 2)

    def test_try_to_insert_fork(self):
        first_block = core.CBlock(hashPrevBlock=chain.genesis_hash, nNonce=1)
        self.chain.try_to_insert_block(first_block, BlockOrigin.public)

        second_block = core.CBlock(hashPrevBlock=chain.genesis_hash, nNonce=2)
        self.chain.try_to_insert_block(second_block, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 2)
        self.assertEqual(self.chain.tips[0].height, 1)
        self.assertEqual(self.chain.tips[1].height, 1)

    def test_try_to_insert_orphan_blocks(self):
        first_block = core.CBlock(hashPrevBlock=chain.genesis_hash)
        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())

        self.chain.try_to_insert_block(second_block, BlockOrigin.public)
        self.chain.try_to_insert_block(first_block, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)
        self.assertEqual(self.chain.tips[0].height, 2)
        self.assertEqual(self.chain.tips[0].prevBlock.height, 1)
        self.assertEqual(len(self.chain.orphan_blocks), 0)

    def test_try_to_insert_two_orphan_blocks(self):
        first_block = core.CBlock(hashPrevBlock=chain.genesis_hash)
        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())
        third_block = core.CBlock(hashPrevBlock=second_block.GetHash())

        self.chain.try_to_insert_block(third_block, BlockOrigin.public)
        self.assertEqual(len(self.chain.orphan_blocks), 1)
        self.chain.try_to_insert_block(second_block, BlockOrigin.public)
        self.assertEqual(len(self.chain.orphan_blocks), 2)
        self.chain.try_to_insert_block(first_block, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)
        self.assertEqual(self.chain.tips[0].height, 3)
        self.assertEqual(self.chain.tips[0].prevBlock.height, 2)
        self.assertEqual(len(self.chain.orphan_blocks), 0)

    def test_get_private_public_fork_no_private_tip(self):
        fork = chain.get_private_public_fork([self.second_block_chain_b])
        self.assertEqual(fork.private_height, 0)
        print(fork.private_tip.hash)
        print()
        self.assertEqual(fork.private_tip.hash, chain.genesis_hash)

        self.assertEqual(fork.public_height, 2)
        self.assertEqual(fork.public_tip.hash, '2b')

    def test_get_private_public_fork_no_public_tip(self):
        fork = chain.get_private_public_fork([self.second_block_chain_a])
        self.assertEqual(fork.public_height, 0)
        self.assertEqual(fork.public_tip.hash, chain.genesis_hash)

        self.assertEqual(fork.private_height, 2)
        self.assertEqual(fork.private_tip.hash, '2a')

    def test_get_private_public_fork_lead_public(self):
        fork = chain.get_private_public_fork([self.second_block_chain_b, self.first_block_chain_a])
        self.assertEqual(fork.private_height, 1)
        self.assertEqual(fork.private_tip.hash, '1a')

        self.assertEqual(fork.public_height, 2)
        self.assertEqual(fork.public_tip.hash, '2b')

    def test_get_private_public_fork_lead_private(self):
        fork = chain.get_private_public_fork([self.first_block_chain_b, self.second_block_chain_a])

        self.assertEqual(fork.private_height, 2)
        self.assertEqual(fork.private_tip.hash, '2a')

        self.assertEqual(fork.public_height, 1)
        self.assertEqual(fork.public_tip.hash, '1b')

    def test_get_private_public_fork_private_transferred(self):
        self.first_block_chain_a.transfer_allowed = True
        self.second_block_chain_a.transfer_allowed = True
        fork = chain.get_private_public_fork([self.first_block_chain_b, self.second_block_chain_a])

        self.assertEqual(fork.private_height, 0)
        self.assertEqual(fork.private_tip.hash, '2a')

        self.assertEqual(fork.public_height, 0)
        self.assertEqual(fork.public_tip.hash, '2a')

    def test_get_private_public_fork_one_private_transferred(self):
        self.first_block_chain_a.transfer_allowed = True
        fork = chain.get_private_public_fork([self.second_block_chain_a, self.first_block_chain_b])

        self.assertEqual(fork.private_height, 2)
        self.assertEqual(fork.private_tip.hash, '2a')

        self.assertEqual(fork.public_height, 1)

    def test_get_private_public_fork_private_fork_point(self):
        third_a_block_chain_a = Block('3a_1', '2a', BlockOrigin.private)
        third_a_block_chain_a.height = 3
        third_a_block_chain_a.prevBlock = self.second_block_chain_a

        third_b_block_chain_a = Block('3a_2', '2a', BlockOrigin.private)
        third_b_block_chain_a.height = 3
        third_b_block_chain_a.prevBlock = self.second_block_chain_a

        fourth_block_chain_a = Block('4a', '3a_1', BlockOrigin.private)
        fourth_block_chain_a.height = 4
        fourth_block_chain_a.prevBlock = third_a_block_chain_a

        fork = chain.get_private_public_fork([fourth_block_chain_a, third_b_block_chain_a, self.second_block_chain_b])

        self.assertEqual(fork.private_height, 4)
        self.assertEqual(fork.private_tip.hash, '4a')

        self.assertEqual(fork.public_height, 2)
        self.assertEqual(fork.public_tip.hash, '2b')

    def test_get_private_public_fork_half_private_fork_transferred(self):
        self.first_block_chain_a.transfer_allowed = True
        self.second_block_chain_a.transfer_allowed = True

        third_a_block_chain_a = Block('3a_1', '2a', BlockOrigin.private)
        third_a_block_chain_a.height = 3
        third_a_block_chain_a.prevBlock = self.second_block_chain_a

        third_b_block_chain_a = Block('3a_2', '2a', BlockOrigin.private)
        third_b_block_chain_a.height = 3
        third_b_block_chain_a.transfer_allowed = True
        third_b_block_chain_a.prevBlock = self.second_block_chain_a

        fourth_block_chain_a = Block('4a', '3a_1', BlockOrigin.private)
        fourth_block_chain_a.height = 4
        fourth_block_chain_a.prevBlock = third_a_block_chain_a

        fork = chain.get_private_public_fork([self.second_block_chain_b, fourth_block_chain_a, third_b_block_chain_a])
        self.assertEqual(fork.private_height, 2)
        self.assertEqual(fork.private_tip.hash, '4a')

        self.assertEqual(fork.public_height, 1)
        self.assertEqual(fork.public_tip.hash, '3a_2')

    def test_get_private_public_fork_longest_private_fork_transferred(self):
        self.first_block_chain_a.transfer_allowed = True
        self.second_block_chain_a.transfer_allowed = True

        third_a_block_chain_a = Block('3a_1', '2a', BlockOrigin.private)
        third_a_block_chain_a.height = 3
        third_a_block_chain_a.transfer_allowed = True
        third_a_block_chain_a.prevBlock = self.second_block_chain_a

        third_b_block_chain_a = Block('3a_2', '2a', BlockOrigin.private)
        third_b_block_chain_a.height = 3
        third_b_block_chain_a.prevBlock = self.second_block_chain_a

        fourth_block_chain_a = Block('4a', '3a_1', BlockOrigin.private)
        fourth_block_chain_a.height = 4
        fourth_block_chain_a.transfer_allowed = True
        fourth_block_chain_a.prevBlock = third_a_block_chain_a

        fork = chain.get_private_public_fork([self.second_block_chain_b, fourth_block_chain_a, third_b_block_chain_a])
        self.assertEqual(fork.private_height, 0)
        self.assertEqual(fork.private_tip.hash, '4a')

        self.assertEqual(fork.public_height, 0)
        self.assertEqual(fork.public_tip.hash, '4a')

    def test_get_private_public_fork_public_fork_point(self):
        third_a_block_chain_b = Block('3b_1', '2b', BlockOrigin.public)
        third_a_block_chain_b.height = 3
        third_a_block_chain_b.prevBlock = self.second_block_chain_b

        third_b_block_chain_b = Block('3b_2', '2b', BlockOrigin.public)
        third_b_block_chain_b.height = 3
        third_b_block_chain_b.prevBlock = self.second_block_chain_b

        fourth_block_chain_b = Block('4b', '3b_1', BlockOrigin.public)
        fourth_block_chain_b.height = 4
        fourth_block_chain_b.prevBlock = third_a_block_chain_b

        fork = chain.get_private_public_fork([fourth_block_chain_b, third_b_block_chain_b, self.second_block_chain_a])
        self.assertEqual(fork.private_height, 2)
        self.assertEqual(fork.private_tip.hash, '2a')

        self.assertEqual(fork.public_height, 4)
        self.assertEqual(fork.public_tip.hash, '4b')

    def test_get_private_public_fork_after_match(self):
        self.first_block_chain_a.transfer_allowed = True
        self.first_block_chain_b.transfer_allowed = True
        fork = chain.get_private_public_fork([self.first_block_chain_a, self.second_block_chain_b])

        self.assertEqual(fork.private_height, 1)
        self.assertEqual(fork.private_tip.hash, '1a')

        self.assertEqual(fork.public_height, 2)
        self.assertEqual(fork.public_tip.hash, '2b')

    def test_process_block_no_change_in_fork(self):
        self.chain.try_to_insert_block = MagicMock()
        self.chain.length_of_fork = MagicMock()

        self.chain.process_block(None, BlockOrigin.public)

        self.assertTrue(self.chain.try_to_insert_block.called)
        self.assertFalse(self.chain.length_of_fork.called)
        self.assertFalse(self.chain.strategy.find_action.called)

    @patch('chain.get_private_public_fork')
    def test_process_block(self, mock):
        self.chain.try_to_insert_block = MagicMock()
        fork_before = Fork("blocka", 2, "blockb", 2)
        fork_after = Fork("blockaa", 1, "blockbb", 1)
        mock.side_effect = [fork_before, fork_after]
        self.chain.execute = MagicMock()

        self.chain.process_block(None, BlockOrigin.public)

        self.assertTrue(self.chain.try_to_insert_block.called)
        self.assertTrue(mock.called)
        self.assertTrue(self.chain.strategy.find_action.called)
        self.assertTrue(self.chain.executor.execute.called)

    @patch('chain.get_private_public_fork')
    def test_process_block_exception_find_action(self, mock):
        self.chain.try_to_insert_block = MagicMock()
        fork_before = Fork("blocka", 2, "blockb", 2)
        fork_after = Fork("blockaa", 1, "blockbb", 1)
        mock.side_effect = [fork_before, fork_after]
        self.chain.strategy.find_action = MagicMock(side_effect=ActionException('mock_exception'))
        self.chain.execute = MagicMock()

        self.chain.process_block(None, BlockOrigin.public)

        self.assertTrue(self.chain.strategy.find_action.called)
        self.assertFalse(self.chain.execute.called)

    @patch('chain.get_private_public_fork')
    def test_process_block_exception_execute_action(self, mock):
        self.chain.try_to_insert_block = MagicMock()
        fork_before = Fork("blocka", 2, "blockb", 2)
        fork_after = Fork("blockaa", 1, "blockbb", 1)
        mock.side_effect = [fork_before, fork_after]
        self.chain.strategy.find_action = MagicMock()
        self.chain.executor.execute = MagicMock(side_effect=ActionException('mock_exception'))

        self.chain.process_block(None, BlockOrigin.public)

        self.assertTrue(self.chain.strategy.find_action.called)
        self.assertTrue(self.chain.executor.execute.called)

    def test_get_relevant_public_tips_mixed(self):
        tips = chain.get_relevant_tips([self.second_block_chain_a, self.second_block_chain_b])

        self.assertEqual(len(tips), 2)
        self.assertTrue(self.second_block_chain_b in tips)
        self.assertTrue(self.second_block_chain_a in tips)

    def test_get_relevant_public_tips_one_tip_too_short_tip(self):
        high_block_chain_b = Block('10b', '0', BlockOrigin.public)
        high_block_chain_b.height = 11

        tips = chain.get_relevant_tips([high_block_chain_b, self.first_block_chain_b])

        self.assertEqual(tips, [high_block_chain_b])

    def test_get_relevant_public_tips_two_tips(self):
        tips = chain.get_relevant_tips([self.first_block_chain_b, self.second_block_chain_b])

        self.assertEqual(len(tips), 2)
        self.assertTrue(self.first_block_chain_b in tips)
        self.assertTrue(self.second_block_chain_b in tips)

    def test_get_highest_block_genesis_block(self):
        tip = chain.get_highest_block([chain.genesis_block], BlockOrigin.private)

        self.assertEqual(tip, chain.genesis_block)

    def test_get_highest_block_same_origin(self):
        tip = chain.get_highest_block([self.first_block_chain_a], BlockOrigin.private)

        self.assertEqual(tip, self.first_block_chain_a)

    def test_get_highest_block_different_origin(self):
        tip = chain.get_highest_block([self.first_block_chain_a], BlockOrigin.public)

        self.assertEqual(tip, chain.genesis_block)

    def test_get_highest_block_different_origin_transfer_allowed(self):
        self.first_block_chain_a.transfer_allowed = True
        tip = chain.get_highest_block([self.first_block_chain_a], BlockOrigin.public)

        self.assertEqual(tip, self.first_block_chain_a)

    def test_get_highest_block_public_tip_lower_then_transferable_public_block(self):
        third_a_block_chain_a = Block('3a', '2a', BlockOrigin.private)
        third_a_block_chain_a.height = 3
        third_a_block_chain_a.prevBlock = self.second_block_chain_a
        self.second_block_chain_a.transfer_allowed = True

        tip = chain.get_highest_block([third_a_block_chain_a, self.first_block_chain_b], BlockOrigin.public)

        self.assertEqual(tip, self.second_block_chain_a)

    def test_get_highest_block_public_tip_same_height_then_transferable_public_block(self):
        self.first_block_chain_a.transfer_allowed = True

        tip = chain.get_highest_block([self.second_block_chain_a, self.first_block_chain_b], BlockOrigin.public)

        self.assertEqual(tip, self.first_block_chain_b)
