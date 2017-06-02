import test_abstractchain
from chain import Chain
from chain import Block
from chainutil import Fork
from mock import MagicMock
from mock import patch
from bitcoin import core
from strategy import BlockOrigin
from strategy import ActionException
import test_util


class ChainTest(test_abstractchain.AbstractChainTest):

    def __init__(self, *args, **kwargs):
        super(ChainTest, self).__init__(*args, **kwargs)
        self.executor = None
        self.strategy = None
        self.chain = None

    def setUp(self):
        super(ChainTest, self).setUp()
        self.executor = MagicMock()
        self.strategy = MagicMock()
        self.chain = Chain(self.executor, self.strategy, test_util.genesis_hash)
        self.chain.strategy = MagicMock()

    def test_try_to_insert_block_without_prev_hash(self):
        block = core.CBlock()
        self.chain.try_to_insert_block(block, BlockOrigin.public)

        self.assertEqual(len(self.chain.blocks), 2)

    def test_try_to_insert_block_two_times(self):
        block = core.CBlock()
        self.chain.try_to_insert_block(block, BlockOrigin.public)
        self.chain.try_to_insert_block(block, BlockOrigin.public)

        self.assertEqual(len(self.chain.blocks), 2)

    def test_try_to_insert_block(self):
        block = core.CBlock(hashPrevBlock=test_util.genesis_hash)
        self.chain.try_to_insert_block(block, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)
        self.assertEqual(self.chain.tips[0].height, 1)

    def test_try_to_insert_two_blocks(self):
        first_block = core.CBlock(hashPrevBlock=test_util.genesis_hash)
        self.chain.try_to_insert_block(first_block, BlockOrigin.public)

        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())
        self.chain.try_to_insert_block(second_block, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)
        self.assertEqual(self.chain.tips[0].height, 2)

    def test_try_to_insert_fork(self):
        first_block = core.CBlock(hashPrevBlock=test_util.genesis_hash, nNonce=1)
        self.chain.try_to_insert_block(first_block, BlockOrigin.public)

        second_block = core.CBlock(hashPrevBlock=test_util.genesis_hash, nNonce=2)
        self.chain.try_to_insert_block(second_block, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 2)
        self.assertEqual(self.chain.tips[0].height, 1)
        self.assertEqual(self.chain.tips[1].height, 1)

    def test_try_to_insert_orphan_blocks(self):
        first_block = core.CBlock(hashPrevBlock=test_util.genesis_hash)
        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())

        self.chain.try_to_insert_block(second_block, BlockOrigin.public)
        self.chain.try_to_insert_block(first_block, BlockOrigin.public)

        self.assertEqual(len(self.chain.tips), 1)
        self.assertEqual(self.chain.tips[0].height, 2)
        self.assertEqual(self.chain.tips[0].prevBlock.height, 1)
        self.assertEqual(len(self.chain.orphan_blocks), 0)

    def test_try_to_insert_two_orphan_blocks(self):
        first_block = core.CBlock(hashPrevBlock=test_util.genesis_hash)
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
        self.chain.initializing = False

        self.chain.process_block(block, BlockOrigin.public)

        self.assertTrue(self.chain.try_to_insert_block.called)
        self.assertTrue(mock.called)
        self.assertTrue(self.chain.strategy.find_action.called)
        self.assertTrue(self.chain.executor.execute.called)

    @patch('bitcoin.core.b2lx')
    @patch('chainutil.get_private_public_fork')
    def test_process_block(self, mock, _):
        self.chain.try_to_insert_block = MagicMock()
        fork = Fork(self.first_block_chain_a, 2, self.first_block_chain_b, 2)
        mock.return_value(fork)
        block = MagicMock()
        self.chain.initializing = True

        self.chain.process_block(block, BlockOrigin.public)

        self.assertTrue(self.chain.try_to_insert_block.called)
        self.assertTrue(mock.called)
        self.assertFalse(self.chain.strategy.find_action.called)
        self.assertFalse(self.chain.executor.execute.called)

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
        self.chain.initializing = False

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
        self.chain.initializing = False

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
        self.assertEqual(retrieved_block.height, 46)

    def test_insert_block_initializing_true(self):
        prevBlock = Block(None, BlockOrigin.private)
        prevBlock.cached_hash = 'hash2'
        prevBlock.height = 45
        block = Block(None, BlockOrigin.private)
        block.cached_hash = 'hash1'
        self.chain.tips = [prevBlock]
        self.chain.initializing = True

        self.chain.insert_block(prevBlock, block)

        retrieved_block = self.chain.tips[0]
        self.assertEqual(retrieved_block, block)
        self.assertEqual(retrieved_block.transfer_allowed, True)

    def test_insert_block_initializing_false(self):
        prevBlock = Block(None, BlockOrigin.private)
        prevBlock.cached_hash = 'hash2'
        prevBlock.height = 45
        block = Block(None, BlockOrigin.private)
        block.cached_hash = 'hash1'
        self.chain.tips = [prevBlock]
        self.chain.initializing = False

        self.chain.insert_block(prevBlock, block)

        retrieved_block = self.chain.tips[0]
        self.assertEqual(retrieved_block, block)
        self.assertEqual(retrieved_block.transfer_allowed, False)

    def test_insert_block_initializing_over(self):
        prevBlock = Block(None, BlockOrigin.private)
        prevBlock.cached_hash = 'hash2'
        prevBlock.height = 45
        block = Block(None, BlockOrigin.private)
        block.cached_hash = 'hash1'
        self.chain.tips = [prevBlock]
        self.chain.initializing = True
        self.chain.start_hash = block.cached_hash

        self.chain.insert_block(prevBlock, block)

        retrieved_block = self.chain.tips[0]
        self.assertEqual(retrieved_block, block)
        self.assertEqual(retrieved_block.transfer_allowed, True)
        self.assertEqual(self.chain.initializing, False)
