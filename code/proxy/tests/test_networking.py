import unittest
from mock import MagicMock
from networking import Networking
from bitcoin import net
from bitcoin import messages
from chain import Block
from chain import BlockOrigin


class NetworkingTest(unittest.TestCase):

    def setUp(self):
        self.networking = Networking()
        self.connection_private = self.networking.connection_private = MagicMock()
        self.connection_public = self.networking.connection_public = MagicMock()
        self.chain = MagicMock()

        self.networking.relay[self.connection_private] = self.connection_public
        self.networking.relay[self.connection_public] = self.connection_private
        self.networking.chain = self.chain

    def test_process_inv_msg_block(self):
        inv = net.CInv()
        inv.type = get_type_key("Block")
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connection_private, msg)

        self.assertTrue(self.connection_private.send.called)
        self.assertEqual(self.connection_private.send.call_args[0][0], 'getdata')
        self.assertFalse(self.connection_public.send.called)

    def test_process_inv_msg_filtered_block(self):
        inv = net.CInv()
        inv.type = get_type_key("FilteredBlock")
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connection_private, msg)

        self.assertFalse(self.connection_private.send.called)
        self.assertFalse(self.connection_public.send.called)

    def test_process_inv_msg_error(self):
        inv = net.CInv()
        inv.type = get_type_key("Error")
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connection_private, msg)

        self.assertFalse(self.connection_private.send.called)
        self.assertTrue(self.connection_public.send.called)
        self.assertEqual(self.connection_public.send.call_args[0][0], 'inv')

        amount_of_inv = len(self.connection_public.send.call_args[0][1])
        self.assertEqual(amount_of_inv, 1)

    def test_process_inv_msg_tx(self):
        inv = net.CInv()
        inv.type = get_type_key("TX")
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connection_private, msg)

        self.assertFalse(self.connection_private.send.called)
        self.assertTrue(self.connection_public.send.called)
        self.assertEqual(self.connection_public.send.call_args[0][0], 'inv')

        amount_of_inv = len(self.connection_public.send.call_args[0][1])
        self.assertEqual(amount_of_inv, 1)

    def test_process_inv_msg_unknown(self):
        inv = net.CInv()
        inv.type = "Unknown"
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connection_private, msg)

        self.assertFalse(self.connection_private.send.called)
        self.assertFalse(self.connection_public.send.called)

    def test_relay_message(self):
        msg = messages.msg_version
        self.networking.relay_message(self.connection_private, msg)

        self.assertFalse(self.connection_private.send.called)
        self.assertTrue(self.connection_public.send.called)
        self.assertEqual(self.connection_public.send.call_args[0][0], msg.command)

    def test_process_block(self):
        msg = messages.msg_version
        self.networking.process_block(self.connection_private, msg)

        self.assertTrue(self.chain.process_block.called)

    def test_transfer_private_blocks(self):
        block1 = Block("hash1", None, BlockOrigin.private)
        block2 = Block("hash2", None, BlockOrigin.private)
        self.networking.transfer_blocks([block1, block2])

        self.assertTrue(block1.transferred)
        self.assertTrue(block2.transferred)
        self.assertTrue(self.networking.connection_public.send.called)
        inv_msg = self.networking.connection_public.send.call_args[0][1]
        self.assertEqual(len(inv_msg), 2)

        self.assertFalse(self.networking.connection_private.send.called)

    def test_transfer_public_blocks(self):
        block1 = Block("hash1", None, BlockOrigin.public)
        block2 = Block("hash2", None, BlockOrigin.public)
        self.networking.transfer_blocks([block1, block2])

        self.assertTrue(block1.transferred)
        self.assertTrue(block2.transferred)
        self.assertFalse(self.connection_public.send.called)

        self.assertTrue(self.connection_private.send.called)
        inv_msg = self.networking.connection_private.send.call_args[0][1]
        self.assertEqual(len(inv_msg), 2)

    def test_transfer_blocks(self):
        block1 = Block("hash1", None, BlockOrigin.public)
        block2 = Block("hash2", None, BlockOrigin.public)
        block3 = Block("hash3", None, BlockOrigin.public)
        block4 = Block("hash4", None, BlockOrigin.private)
        block5 = Block("hash5", None, BlockOrigin.private)
        self.networking.transfer_blocks([block1, block2, block3, block4, block5])

        self.assertTrue(self.connection_public.send.called)
        inv_msg = self.networking.connection_private.send.call_args[0][1]
        self.assertEqual(len(inv_msg), 3)

        self.assertTrue(self.connection_public.send.called)
        inv_msg = self.networking.connection_public.send.call_args[0][1]
        self.assertEqual(len(inv_msg), 2)


def get_type_key(msg_type):
    for key in net.CInv.typemap.keys():
        if net.CInv.typemap[key] == msg_type:
            return key
