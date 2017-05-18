import unittest
from chain import Block
from chain import Chain
import chain
import chainutil
from mock import MagicMock
from strategy import BlockOrigin


class ChainUtilTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(ChainUtilTest, self).__init__(*args, **kwargs)

        self.executor = None
        self.strategy = None
        self.chain = None
        self.first_block_chain_a = None
        self.second_block_chain_a = None
        self.third_a_block_chain_a = None
        self.third_b_block_chain_a = None
        self.fourth_block_chain_a = None
        self.first_block_chain_b = None
        self.second_block_chain_b = None
        self.third_a_block_chain_b = None
        self.third_b_block_chain_b = None
        self.fourth_block_chain_b = None

    def setUp(self):
        self.executor = MagicMock()
        self.strategy = MagicMock()
        self.chain = Chain(self.executor, self.strategy)
        self.chain.strategy = MagicMock()

        self.first_block_chain_a = Block(None, BlockOrigin.private)
        self.first_block_chain_a.height = 1
        self.first_block_chain_a.prevBlock = chain.genesis_block
        self.first_block_chain_a.cached_hash = '1a'

        self.second_block_chain_a = Block(None, BlockOrigin.private)
        self.second_block_chain_a.height = 2
        self.second_block_chain_a.prevBlock = self.first_block_chain_a
        self.second_block_chain_a.cached_hash = '2a'

        self.third_a_block_chain_a = Block(None, BlockOrigin.private)
        self.third_a_block_chain_a.height = 3
        self.third_a_block_chain_a.prevBlock = self.second_block_chain_a
        self.third_a_block_chain_a.cached_hash = '3a_1'

        self.third_b_block_chain_a = Block(None, BlockOrigin.private)
        self.third_b_block_chain_a.height = 3
        self.third_b_block_chain_a.prevBlock = self.second_block_chain_a
        self.third_b_block_chain_a.cached_hash = '3a_2'

        self.fourth_block_chain_a = Block(None, BlockOrigin.private)
        self.fourth_block_chain_a.height = 4
        self.fourth_block_chain_a.prevBlock = self.third_a_block_chain_a
        self.fourth_block_chain_a.cached_hash = '4a'

        self.first_block_chain_b = Block(None, BlockOrigin.public)
        self.first_block_chain_b.height = 1
        self.first_block_chain_b.prevBlock = chain.genesis_block
        self.first_block_chain_b.cached_hash = '1b'

        self.second_block_chain_b = Block(None, BlockOrigin.public)
        self.second_block_chain_b.height = 2
        self.second_block_chain_b.prevBlock = self.first_block_chain_b
        self.second_block_chain_b.cached_hash = '2b'

        self.third_a_block_chain_b = Block(None, BlockOrigin.public)
        self.third_a_block_chain_b.height = 3
        self.third_a_block_chain_b.prevBlock = self.second_block_chain_b
        self.third_a_block_chain_b.cached_hash = '3b_1'

        self.third_b_block_chain_b = Block(None, BlockOrigin.public)
        self.third_b_block_chain_b.height = 3
        self.third_b_block_chain_b.prevBlock = self.second_block_chain_b
        self.third_b_block_chain_b.cached_hash = '3b_2'

        self.fourth_block_chain_b = Block(None, BlockOrigin.public)
        self.fourth_block_chain_b.height = 4
        self.fourth_block_chain_b.prevBlock = self.third_a_block_chain_b
        self.fourth_block_chain_b.cached_hash = '4b'

    def test_get_private_public_fork_no_private_tip(self):
        fork = chainutil.get_private_public_fork([self.second_block_chain_b])
        self.assertEqual(fork.private_height, 0)
        self.assertEqual(fork.private_tip.hash(), chain.genesis_hash)

        self.assertEqual(fork.public_height, 2)
        self.assertEqual(fork.public_tip.hash(), '2b')

    def test_get_private_public_fork_no_public_tip(self):
        fork = chainutil.get_private_public_fork([self.second_block_chain_a])
        self.assertEqual(fork.public_height, 0)
        self.assertEqual(fork.public_tip.hash(), chain.genesis_hash)

        self.assertEqual(fork.private_height, 2)
        self.assertEqual(fork.private_tip.hash(), '2a')

    def test_get_private_public_fork_lead_public(self):
        fork = chainutil.get_private_public_fork([self.second_block_chain_b, self.first_block_chain_a])
        self.assertEqual(fork.private_height, 1)
        self.assertEqual(fork.private_tip.hash(), '1a')

        self.assertEqual(fork.public_height, 2)
        self.assertEqual(fork.public_tip.hash(), '2b')

    def test_get_private_public_fork_lead_private(self):
        fork = chainutil.get_private_public_fork([self.first_block_chain_b, self.second_block_chain_a])

        self.assertEqual(fork.private_height, 2)
        self.assertEqual(fork.private_tip.hash(), '2a')

        self.assertEqual(fork.public_height, 1)
        self.assertEqual(fork.public_tip.hash(), '1b')

    def test_get_private_public_fork_private_transferred(self):
        self.first_block_chain_a.transfer_allowed = True
        self.second_block_chain_a.transfer_allowed = True
        fork = chainutil.get_private_public_fork([self.first_block_chain_b, self.second_block_chain_a])

        self.assertEqual(fork.private_height, 0)
        self.assertEqual(fork.private_tip.hash(), '2a')

        self.assertEqual(fork.public_height, 0)
        self.assertEqual(fork.public_tip.hash(), '2a')

    def test_get_private_public_fork_one_private_transferred(self):
        self.first_block_chain_a.transfer_allowed = True
        fork = chainutil.get_private_public_fork([self.second_block_chain_a, self.first_block_chain_b])

        self.assertEqual(fork.private_height, 2)
        self.assertEqual(fork.private_tip.hash(), '2a')

        self.assertEqual(fork.public_height, 1)

    def test_get_private_public_fork_private_fork_point(self):
        fork = chainutil.get_private_public_fork(
            [self.fourth_block_chain_a, self.third_b_block_chain_a, self.second_block_chain_b])

        self.assertEqual(fork.private_height, 4)
        self.assertEqual(fork.private_tip.hash(), '4a')

        self.assertEqual(fork.public_height, 2)
        self.assertEqual(fork.public_tip.hash(), '2b')

    def test_get_private_public_fork_half_private_fork_transferred(self):
        self.first_block_chain_a.transfer_allowed = True
        self.second_block_chain_a.transfer_allowed = True
        self.third_b_block_chain_a.transfer_allowed = True

        fork = chainutil.get_private_public_fork(
            [self.second_block_chain_b, self.fourth_block_chain_a, self.third_b_block_chain_a])

        self.assertEqual(fork.private_height, 2)
        self.assertEqual(fork.private_tip.hash(), '4a')

        self.assertEqual(fork.public_height, 1)
        self.assertEqual(fork.public_tip.hash(), '3a_2')

    def test_get_private_public_fork_longest_private_fork_transferred(self):
        self.first_block_chain_a.transfer_allowed = True
        self.second_block_chain_a.transfer_allowed = True
        self.third_a_block_chain_a.transfer_allowed = True
        self.fourth_block_chain_a.transfer_allowed = True

        fork = chainutil.get_private_public_fork(
            [self.second_block_chain_b, self.fourth_block_chain_a, self.third_b_block_chain_a])
        self.assertEqual(fork.private_height, 0)
        self.assertEqual(fork.private_tip.hash(), '4a')

        self.assertEqual(fork.public_height, 0)
        self.assertEqual(fork.public_tip.hash(), '4a')

    def test_get_private_public_fork_public_fork_point(self):
        fork = chainutil.get_private_public_fork(
            [self.fourth_block_chain_b, self.third_b_block_chain_b, self.second_block_chain_a])
        self.assertEqual(fork.private_height, 2)
        self.assertEqual(fork.private_tip.hash(), '2a')

        self.assertEqual(fork.public_height, 4)
        self.assertEqual(fork.public_tip.hash(), '4b')

    def test_get_private_public_fork_after_match(self):
        self.first_block_chain_a.transfer_allowed = True
        self.first_block_chain_b.transfer_allowed = True
        fork = chainutil.get_private_public_fork([self.first_block_chain_a, self.second_block_chain_b])

        self.assertEqual(fork.private_height, 1)
        self.assertEqual(fork.private_tip.hash(), '1a')

        self.assertEqual(fork.public_height, 2)
        self.assertEqual(fork.public_tip.hash(), '2b')

    def test_get_relevant_public_tips_two_tips(self):
        tips = chainutil.get_relevant_tips([self.first_block_chain_b, self.second_block_chain_b])

        self.assertEqual(len(tips), 2)
        self.assertTrue(self.first_block_chain_b in tips)
        self.assertTrue(self.second_block_chain_b in tips)

    def test_get_highest_block_genesis_block(self):
        tip = chainutil.get_highest_block([chain.genesis_block], BlockOrigin.private)

        self.assertEqual(tip, chain.genesis_block)

    def test_get_highest_block_same_origin(self):
        tip = chainutil.get_highest_block([self.first_block_chain_a], BlockOrigin.private)

        self.assertEqual(tip, self.first_block_chain_a)

    def test_get_highest_block_different_origin(self):
        tip = chainutil.get_highest_block([self.first_block_chain_a], BlockOrigin.public)

        self.assertEqual(tip, chain.genesis_block)

    def test_get_highest_block_different_origin_transfer_allowed(self):
        self.first_block_chain_a.transfer_allowed = True
        tip = chainutil.get_highest_block([self.first_block_chain_a], BlockOrigin.public)

        self.assertEqual(tip, self.first_block_chain_a)

    def test_get_highest_block_public_tip_lower_then_transferable_public_block(self):
        self.second_block_chain_a.transfer_allowed = True

        tip = chainutil.get_highest_block([self.third_a_block_chain_a, self.first_block_chain_b], BlockOrigin.public)

        self.assertEqual(tip, self.second_block_chain_a)

    def test_get_highest_block_public_tip_same_height_then_transferable_public_block(self):
        self.first_block_chain_a.transfer_allowed = True

        tip = chainutil.get_highest_block([self.second_block_chain_a, self.first_block_chain_b], BlockOrigin.public)

        self.assertEqual(tip, self.first_block_chain_b)
