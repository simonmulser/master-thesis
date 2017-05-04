import unittest
from chain import Chain
from chain import Block
from chain import Fork
from chain import get_private_public_fork
from mock import MagicMock
from mock import patch
from bitcoin import core
from strategy import BlockOrigin
from strategy import Action
from strategy import ActionException


class ChainTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(ChainTest, self).__init__(*args, **kwargs)

        self.networking = None
        self.chain = None
        self.first_block_chain_a = None
        self.second_block_chain_a = None
        self.first_block_chain_b = None
        self.second_block_chain_b = None

    def setUp(self):
        self.networking = MagicMock()
        self.chain = Chain(self.networking)
        self.chain.strategy = MagicMock()

        self.first_block_chain_b = Block('1b', '0', BlockOrigin.public)
        self.first_block_chain_b.height = 1
        self.first_block_chain_b.prevBlock = genesis_block

        self.second_block_chain_b = Block('2b', '1b', BlockOrigin.public)
        self.second_block_chain_b.height = 2
        self.second_block_chain_b.prevBlock = self.first_block_chain_b

        self.first_block_chain_a = Block('1a', '0', BlockOrigin.private)
        self.first_block_chain_a.height = 1
        self.first_block_chain_a.prevBlock = genesis_block

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
        fork = get_private_public_fork([self.second_block_chain_b])
        self.assertEqual(fork.private_height, 0)
        self.assertEqual(fork.private_tip.hash, '2b')

        self.assertEqual(fork.public_height, 0)
        self.assertEqual(fork.public_tip.hash, '2b')

    def test_get_private_public_fork_lead_public(self):
        fork = get_private_public_fork([self.second_block_chain_b, self.first_block_chain_a])
        self.assertEqual(fork.private_height, 1)
        self.assertEqual(fork.private_tip.hash, '1a')

        self.assertEqual(fork.public_height, 2)
        self.assertEqual(fork.public_tip.hash, '2b')

    def test_get_private_public_fork_lead_private(self):
        fork = get_private_public_fork([self.first_block_chain_b, self.second_block_chain_a])

        self.assertEqual(fork.private_height, 2)
        self.assertEqual(fork.private_tip.hash, '2a')

        self.assertEqual(fork.public_height, 1)
        self.assertEqual(fork.public_tip.hash, '1b')

    def test_get_private_public_fork_private_transferred(self):
        self.first_block_chain_a.transfer_allowed = True
        self.second_block_chain_a.transfer_allowed = True
        fork = get_private_public_fork([self.first_block_chain_b, self.second_block_chain_a])

        self.assertEqual(fork.private_height, 0)
        self.assertEqual(fork.private_tip.hash, '2a')

        self.assertEqual(fork.public_height, 0)
        self.assertEqual(fork.public_tip.hash, '2a')

    def test_get_private_public_fork_one_private_transferred(self):
        self.first_block_chain_a.transfer_allowed = True
        fork = get_private_public_fork([self.first_block_chain_b, self.second_block_chain_a])

        self.assertEqual(fork.private_height, 2)
        self.assertEqual(fork.private_tip.hash, '2a')

        self.assertEqual(fork.public_height, 1)
        self.assertEqual(fork.public_tip.hash, '1b')

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

        fork = get_private_public_fork([self.second_block_chain_b, fourth_block_chain_a, third_b_block_chain_a])
        self.assertEqual(fork.private_height, 4)
        self.assertEqual(fork.private_tip.hash, '4a')

        self.assertEqual(fork.public_height, 3)
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

        fork = get_private_public_fork([self.second_block_chain_b, fourth_block_chain_a, third_b_block_chain_a])
        self.assertEqual(fork.private_height, 3)
        self.assertEqual(fork.private_tip.hash, '3a_2')

        self.assertEqual(fork.public_height, 4)
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

        fork = get_private_public_fork([fourth_block_chain_b, third_b_block_chain_b, self.second_block_chain_a])
        self.assertEqual(fork.private_height, 2)
        self.assertEqual(fork.private_tip.hash, '2a')

        self.assertEqual(fork.public_height, 4)
        self.assertEqual(fork.public_tip.hash, '4b')

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
        fork_before = Fork(2, 2)
        fork_after = Fork(1, 1)
        mock.side_effect = [fork_before, fork_after]
        self.chain.execute_action = MagicMock()

        self.chain.process_block(None, BlockOrigin.public)

        self.assertTrue(self.chain.try_to_insert_block.called)
        self.assertTrue(mock.called)
        self.assertTrue(self.chain.strategy.find_action.called)
        self.assertTrue(self.chain.execute_action.called)

    @patch('chain.get_private_public_fork')
    def test_process_block_exception_find_action(self, mock):
        self.chain.try_to_insert_block = MagicMock()
        fork_before = Fork(2, 2)
        fork_after = Fork(1, 1)
        mock.side_effect = [fork_before, fork_after]
        self.chain.strategy.find_action = MagicMock(side_effect=ActionException('mock_exception'))
        self.chain.execute_action = MagicMock()

        self.chain.process_block(None, BlockOrigin.public)

        self.assertTrue(self.chain.strategy.find_action.called)
        self.assertFalse(self.chain.execute_action.called)

    @patch('chain.get_private_public_fork')
    def test_process_block_exception_execute_action(self, mock):
        self.chain.try_to_insert_block = MagicMock()
        fork_before = Fork(2, 2)
        fork_after = Fork(1, 1)
        mock.side_effect = [fork_before, fork_after]
        self.chain.strategy.find_action = MagicMock()
        self.chain.execute_action = MagicMock(side_effect=ActionException('mock_exception'))

        self.chain.process_block(None, BlockOrigin.public)

        self.assertTrue(self.chain.strategy.find_action.called)
        self.assertTrue(self.chain.execute_action.called)

    def test_match_same_height(self):
        block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        self.chain.try_to_insert_block(block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(block_chain_b, BlockOrigin.public)

        fork = get_private_public_fork(self.chain.tips)

        self.chain.execute_action(Action.match, fork.private_tip, fork.public_tip)

        self.assertTrue(self.chain.networking.send_inv.called)

        hashes_blocks_transfer_unallowed = [block.hash for block in self.chain.networking.send_inv.call_args[0][0]]

        self.assertEqual(len(hashes_blocks_transfer_unallowed), 2)
        self.assertTrue(block_chain_a.GetHash() in hashes_blocks_transfer_unallowed)
        self.assertTrue(block_chain_b.GetHash() in hashes_blocks_transfer_unallowed)

    def test_match_lead_private(self):
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_a = core.CBlock(hashPrevBlock=first_block_chain_a.GetHash())
        block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        self.chain.try_to_insert_block(first_block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(second_block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(block_chain_b, BlockOrigin.public)

        fork = get_private_public_fork(self.chain.tips)

        self.chain.execute_action(Action.match, fork.private_tip, fork.public_tip)

        self.assertTrue(self.chain.networking.send_inv.called)

        hashes_blocks_transfer_unallowed = [block.hash for block in self.chain.networking.send_inv.call_args[0][0]]

        self.assertEqual(len(hashes_blocks_transfer_unallowed), 2)
        self.assertTrue(first_block_chain_a.GetHash() in hashes_blocks_transfer_unallowed)
        self.assertTrue(block_chain_b.GetHash() in hashes_blocks_transfer_unallowed)

    def test_match_lead_public(self):
        private_tip = Block(None, None, None)
        private_tip.height = 1

        public_tip = Block(None, None, None)
        public_tip.height = 2

        with self.assertRaisesRegexp(ActionException, "private tip.*must >= then public tip.*match.*"):
            self.chain.execute_action(Action.match, private_tip, public_tip)

    def test_override_lead_public(self):
        private_tip = Block(None, None, None)
        private_tip.height = 1

        public_tip = Block(None, None, None)
        public_tip.height = 2

        with self.assertRaisesRegexp(ActionException, "private tip.*must > then public tip.*override.*"):
            self.chain.execute_action(Action.override, private_tip, public_tip)

    def test_override_same_height(self):
        private_tip = Block(None, None, None)
        private_tip.height = 2

        public_tip = Block(None, None, None)
        public_tip.height = 2

        with self.assertRaisesRegexp(ActionException, "private tip.*must > then public tip.*override.*"):
            self.chain.execute_action(Action.override, private_tip, public_tip)

    def test_override_lead_private(self):
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_a = core.CBlock(hashPrevBlock=first_block_chain_a.GetHash())
        block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        self.chain.try_to_insert_block(first_block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(second_block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(block_chain_b, BlockOrigin.public)

        fork = get_private_public_fork(self.chain.tips)

        self.chain.execute_action(Action.override, fork.private_tip, fork.public_tip)

        self.assertTrue(self.chain.networking.send_inv.called)

        hashes_blocks_transfer_unallowed = [block.hash for block in self.chain.networking.send_inv.call_args[0][0]]

        self.assertEqual(len(hashes_blocks_transfer_unallowed), 3)
        self.assertTrue(first_block_chain_a.GetHash() in hashes_blocks_transfer_unallowed)
        self.assertTrue(second_block_chain_a.GetHash() in hashes_blocks_transfer_unallowed)
        self.assertTrue(block_chain_b.GetHash() in hashes_blocks_transfer_unallowed)

    def test_override_two_blocks_lead_private(self):
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_a = core.CBlock(hashPrevBlock=first_block_chain_a.GetHash())
        third_block_chain_a = core.CBlock(hashPrevBlock=second_block_chain_a.GetHash())
        block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        self.chain.try_to_insert_block(first_block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(second_block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(third_block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(block_chain_b, BlockOrigin.public)

        fork = get_private_public_fork(self.chain.tips)

        self.chain.execute_action(Action.override, fork.private_tip, fork.public_tip)

        self.assertTrue(self.chain.networking.send_inv.called)

        hashes_blocks_transfer_unallowed = [block.hash for block in self.chain.networking.send_inv.call_args[0][0]]

        self.assertEqual(len(hashes_blocks_transfer_unallowed), 3)
        self.assertTrue(first_block_chain_a.GetHash() in hashes_blocks_transfer_unallowed)
        self.assertTrue(second_block_chain_a.GetHash() in hashes_blocks_transfer_unallowed)
        self.assertTrue(block_chain_b.GetHash() in hashes_blocks_transfer_unallowed)

    def test_adopt_private_lead(self):
        private_tip = Block(None, None, None)
        private_tip.height = 3

        public_tip = Block(None, None, None)
        public_tip.height = 2

        with self.assertRaisesRegexp(ActionException, "public tip.*must > then private tip.*adopt.*"):
            self.chain.execute_action(Action.adopt, private_tip, public_tip)

    def test_adopt_same_height(self):
        private_tip = Block(None, None, None)
        private_tip.height = 2

        public_tip = Block(None, None, None)
        public_tip.height = 2

        with self.assertRaisesRegexp(ActionException, "public tip.*must > then private tip.*adopt.*"):
            self.chain.execute_action(Action.adopt, private_tip, public_tip)

    def test_adopt_lead_public(self):
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_b = core.CBlock(hashPrevBlock=first_block_chain_b.GetHash())
        block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        self.chain.try_to_insert_block(first_block_chain_b, BlockOrigin.public)
        self.chain.try_to_insert_block(second_block_chain_b, BlockOrigin.public)
        self.chain.try_to_insert_block(block_chain_a, BlockOrigin.private)

        fork = get_private_public_fork(self.chain.tips)

        self.chain.execute_action(Action.adopt, fork.private_tip, fork.public_tip)

        self.assertTrue(self.chain.networking.send_inv.called)

        hashes_blocks_transfer_unallowed = [block.hash for block in self.chain.networking.send_inv.call_args[0][0]]

        self.assertEqual(len(hashes_blocks_transfer_unallowed), 2)
        self.assertTrue(first_block_chain_b.GetHash() in hashes_blocks_transfer_unallowed)
        self.assertTrue(second_block_chain_b.GetHash() in hashes_blocks_transfer_unallowed)

    def test_adopt_two_blocks_lead_public(self):
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        second_block_chain_b = core.CBlock(hashPrevBlock=first_block_chain_b.GetHash())
        third_block_chain_b = core.CBlock(hashPrevBlock=second_block_chain_b.GetHash())
        block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        self.chain.try_to_insert_block(first_block_chain_b, BlockOrigin.public)
        self.chain.try_to_insert_block(second_block_chain_b, BlockOrigin.public)
        self.chain.try_to_insert_block(third_block_chain_b, BlockOrigin.public)
        self.chain.try_to_insert_block(block_chain_a, BlockOrigin.private)

        fork = get_private_public_fork(self.chain.tips)

        self.chain.execute_action(Action.adopt, fork.private_tip, fork.public_tip)

        self.assertTrue(self.chain.networking.send_inv.called)

        hashes_blocks_transfer_unallowed = [block.hash for block in self.chain.networking.send_inv.call_args[0][0]]

        self.assertEqual(len(hashes_blocks_transfer_unallowed), 3)
        self.assertTrue(first_block_chain_b.GetHash() in hashes_blocks_transfer_unallowed)
        self.assertTrue(second_block_chain_b.GetHash() in hashes_blocks_transfer_unallowed)
        self.assertTrue(third_block_chain_b.GetHash() in hashes_blocks_transfer_unallowed)

    def test_execute_action_transfer_allowed_set(self):
        block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)

        self.chain.try_to_insert_block(block_chain_a, BlockOrigin.private)
        self.chain.try_to_insert_block(block_chain_b, BlockOrigin.public)

        fork = get_private_public_fork(self.chain.tips)

        self.chain.execute_action(Action.match, fork.private_tip, fork.public_tip)

        self.assertTrue(self.chain.networking.send_inv.called)
        self.assertEqual(len(self.chain.networking.send_inv.call_args[0][0]), 2)
        for block in self.chain.networking.send_inv.call_args[0][0]:
            self.assertTrue(block.transfer_allowed)


def genesis_hash():
    return core.CoreRegTestParams.GENESIS_BLOCK.GetHash()

genesis_block = Block(genesis_hash(), None, BlockOrigin.public)
genesis_block.transfer_allowed = True
