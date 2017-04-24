import unittest
import mock
from chain import Chain
from bitcoin import messages
from bitcoin import core
import logging


class ChainTest(unittest.TestCase):

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_block(self, connection):
        logic = Chain()
        block = core.CBlock()
        msg = messages.msg_block
        msg.block = block
        logic.process_block(connection, msg)

        self.assertTrue(block.GetHash() in logic.blocks)
        self.assertEqual(len(logic.blocks), 2)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_block_two_times(self, connection):
        logic = Chain()
        block = core.CBlock()
        msg = messages.msg_block
        msg.block = block
        logic.process_block(connection, msg)
        logic.process_block(connection, msg)

        self.assertEqual(len(logic.blocks), 2)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_block(self, connection):
        logic = Chain()
        block = core.CBlock(hashPrevBlock=genesis_hash())
        msg = messages.msg_block
        msg.block = block
        logic.process_block(connection, msg)

        self.assertEqual( len(logic.tips), 1)
        self.assertEqual( logic.tips[0].height, 1)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_two_block(self, connection):
        logic = Chain()
        first_block = core.CBlock(hashPrevBlock=genesis_hash())
        msg = messages.msg_block
        msg.block = first_block
        logic.process_block(connection, msg)

        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())
        msg.block = second_block
        logic.process_block(connection, msg)

        self.assertEqual( len(logic.tips), 1)
        self.assertEqual( logic.tips[0].height, 2)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_fork(self, connection):
        logic = Chain()
        first_block = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        msg = messages.msg_block
        msg.block = first_block
        logic.process_block(connection, msg)

        second_block = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)
        msg.block = second_block
        logic.process_block(connection, msg)

        self.assertEqual(len(logic.tips), 2)
        self.assertEqual(logic.tips[0].height, 1)
        self.assertEqual(logic.tips[1].height, 1)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_orphan_blocks(self, connection):
        logic = Chain()
        first_block = core.CBlock(hashPrevBlock=genesis_hash())
        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())
        msg = messages.msg_block
        msg.block = second_block
        logic.process_block(connection, msg)

        msg.block = first_block
        logic.process_block(connection, msg)

        self.assertEqual(len(logic.tips), 1)
        self.assertEqual(logic.tips[0].height, 2)
        self.assertEqual(logic.tips[0].prevBlock.height, 1)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_two_orphan_blocks(self, connection):
        logic = Chain()
        first_block = core.CBlock(hashPrevBlock=genesis_hash())
        second_block = core.CBlock(hashPrevBlock=first_block.GetHash())
        third_block = core.CBlock(hashPrevBlock=second_block.GetHash())

        msg = messages.msg_block
        msg.block = third_block
        logic.process_block(connection, msg)

        msg.block = second_block
        logic.process_block(connection, msg)

        msg.block = first_block
        logic.process_block(connection, msg)

        self.assertEqual(len(logic.tips), 1)
        self.assertEqual(logic.tips[0].height, 3)
        self.assertEqual(logic.tips[0].prevBlock.height, 2)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_chain_length(self, connection):
        logic = Chain()
        first_block_chain_a = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=1)
        first_block_chain_b = core.CBlock(hashPrevBlock=genesis_hash(), nNonce=2)
        second_block_chain_a = core.CBlock(hashPrevBlock=first_block_chain_a.GetHash())
        second_block_chain_b = core.CBlock(hashPrevBlock=first_block_chain_b.GetHash())
        third_block_chain_a = core.CBlock(hashPrevBlock=second_block_chain_a.GetHash())

        msg = messages.msg_block
        msg.block = second_block_chain_b
        logic.process_block(connection, msg)

        msg.block = first_block_chain_b
        logic.process_block(connection, msg)

        self.assertEqual(len(logic.tips), 1)
        self.assertEqual(logic.chain_length(), 2)

        msg.block = first_block_chain_a
        logic.process_block(connection, msg)

        msg.block = second_block_chain_a
        logic.process_block(connection, msg)

        msg.block = third_block_chain_a
        logic.process_block(connection, msg)

        self.assertEqual(len(logic.tips), 2)
        self.assertEqual(logic.chain_length(), 3)


def genesis_hash():
    return core.CoreRegTestParams.GENESIS_BLOCK.GetHash()