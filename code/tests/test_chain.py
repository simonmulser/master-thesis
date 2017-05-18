import unittest
from chain import Chain
from chain import Block
from chainutil import Fork
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

    @patch('bitcoin.core.b2lx')
    def test_process_block_no_change_in_fork(self, _):
        self.chain.try_to_insert_block = MagicMock()
        self.chain.length_of_fork = MagicMock()
        block = MagicMock()

        self.chain.process_block(block, BlockOrigin.public)

        self.assertTrue(self.chain.try_to_insert_block.called)
        self.assertFalse(self.chain.length_of_fork.called)
        self.assertFalse(self.chain.strategy.find_action.called)

    @patch('bitcoin.core.b2lx')
    @patch('chainutil.get_private_public_fork')
    def test_process_block(self, mock, _):
        self.chain.try_to_insert_block = MagicMock()
        fork_before = Fork(self.first_block_chain_a, 2, self.first_block_chain_b, 2)
        fork_after = Fork(self.second_block_chain_a, 1, self.second_block_chain_b, 1)
        mock.side_effect = [fork_before, fork_after]
        self.chain.execute = MagicMock()
        block = MagicMock()

        self.chain.process_block(block, BlockOrigin.public)

        self.assertTrue(self.chain.try_to_insert_block.called)
        self.assertTrue(mock.called)
        self.assertTrue(self.chain.strategy.find_action.called)
        self.assertTrue(self.chain.executor.execute.called)

    @patch('bitcoin.core.b2lx')
    @patch('chainutil.get_private_public_fork')
    def test_process_block_exception_find_action(self, mock, _):
        self.chain.try_to_insert_block = MagicMock()
        fork_before = Fork(self.first_block_chain_a, 2, self.first_block_chain_b, 2)
        fork_after = Fork(self.second_block_chain_a, 1, self.second_block_chain_b, 1)
        mock.side_effect = [fork_before, fork_after]
        self.chain.strategy.find_action = MagicMock(side_effect=ActionException('mock_exception'))
        self.chain.execute = MagicMock()
        block = MagicMock()

        self.chain.process_block(block, BlockOrigin.public)

        self.assertTrue(self.chain.strategy.find_action.called)
        self.assertFalse(self.chain.execute.called)

    @patch('bitcoin.core.b2lx')
    @patch('chainutil.get_private_public_fork')
    def test_process_block_exception_execute_action(self, mock, _):
        self.chain.try_to_insert_block = MagicMock()
        fork_before = Fork(self.first_block_chain_a, 2, self.first_block_chain_b, 2)
        fork_after = Fork(self.second_block_chain_a, 1, self.second_block_chain_b, 1)
        mock.side_effect = [fork_before, fork_after]
        self.chain.strategy.find_action = MagicMock()
        self.chain.executor.execute = MagicMock(side_effect=ActionException('mock_exception'))
        block = MagicMock()

        self.chain.process_block(block, BlockOrigin.public)

        self.assertTrue(self.chain.strategy.find_action.called)
        self.assertTrue(self.chain.executor.execute.called)

    def test_insert_block(self):
        prevBlock = Block(None, BlockOrigin.private)
        prevBlock.cached_hash = 'hash2'
        prevBlock.height = 45
        block = Block(None, BlockOrigin.private)
        block.cached_hash = 'hash1'
        self.chain.tips = [prevBlock]

        self.chain.insert_block(prevBlock, block)

        self.assertFalse(prevBlock in self.chain.tips)
        self.assertEqual(len(self.chain.tips), 1)

        retrieved_block = self.chain.tips[0]
        self.assertEqual(retrieved_block, block)
        self.assertEqual(retrieved_block.prevBlock, prevBlock)
        self.assertEqual(retrieved_block.prevBlock.nextBlock, block)
        self.assertEqual(retrieved_block.height, 46)
