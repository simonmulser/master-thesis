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

        self.assertTrue(block.GetHash() in logic.blocks)
        self.assertEqual(len(logic.blocks), 2)


def get_type_key(msg_type):
    for key in net.CInv.typemap.keys():
        if net.CInv.typemap[key] == msg_type:
            return key