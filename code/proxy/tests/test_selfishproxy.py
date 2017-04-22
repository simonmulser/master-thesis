import unittest
import mock
from selfishlogic import SelfishLogic
from bitcoin import net
from bitcoin import messages
from bitcoin import core


class SelfishProxyTest(unittest.TestCase):

    def test_selfishproxy(self):
        assert 1 == 1

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_inv_msg_block(self, connection):
        logic = SelfishLogic()
        inv = net.CInv()
        inv.type = get_type_key("Block")
        msg = messages.msg_inv
        msg.inv = [inv]
        logic.process_inv_msg(connection, msg)

        self.assertTrue(connection.send.called)
        self.assertEqual(connection.send.call_args[0][0], 'getdata')

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_inv_msg_filtered_block(self, connection):
        logic = SelfishLogic()
        inv = net.CInv()
        inv.type = get_type_key("FilteredBlock")
        msg = messages.msg_inv
        msg.inv = [inv]
        logic.process_inv_msg(connection, msg)

        self.assertFalse(connection.send.called)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_inv_msg_error(self, connection):
        logic = SelfishLogic()
        inv = net.CInv()
        inv.type = get_type_key("Error")
        msg = messages.msg_inv
        msg.inv = [inv]
        logic.process_inv_msg(connection, msg)

        self.assertFalse(connection.send.called)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_inv_msg_tx(self, connection):
        logic = SelfishLogic()
        inv = net.CInv()
        inv.type = get_type_key("TX")
        msg = messages.msg_inv
        msg.inv = [inv]
        logic.process_inv_msg(connection, msg)

        self.assertFalse(connection.send.called)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_inv_msg_error(self, connection):
        logic = SelfishLogic()
        inv = net.CInv()
        inv.type = "Unknown"
        msg = messages.msg_inv
        msg.inv = [inv]
        logic.process_inv_msg(connection, msg)

        self.assertFalse(connection.send.called)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_block(self, connection):
        logic = SelfishLogic()
        block = core.CBlock()
        msg = messages.msg_block
        msg.block = block
        logic.process_block(connection, msg)

        self.assertTrue(block.GetHash() in logic.blocks)
        self.assertEqual(len(logic.blocks), 2)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_block_two_times(self, connection):
        logic = SelfishLogic()
        block = core.CBlock()
        msg = messages.msg_block
        msg.block = block
        logic.process_block(connection, msg)
        logic.process_block(connection, msg)

        self.assertEqual(len(logic.blocks), 2)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_block(self, connection):
        logic = SelfishLogic()
        block = core.CBlock(hashPrevBlock=genesis_hash())
        msg = messages.msg_block
        msg.block = block
        logic.process_block(connection, msg)

        self.assertEqual( len(logic.tips), 1)
        self.assertEqual( logic.tips[0].height, 1)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_two_block(self, connection):
        logic = SelfishLogic()
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
        logic = SelfishLogic()
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
        logic = SelfishLogic()
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
        logic = SelfishLogic()
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


def get_type_key(msg_type):
    for key in net.CInv.typemap.keys():
        if net.CInv.typemap[key] == msg_type:
            return key


def genesis_hash():
    return core.CoreRegTestParams.GENESIS_BLOCK.GetHash()
