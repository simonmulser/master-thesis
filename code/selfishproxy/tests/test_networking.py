import unittest
from mock import MagicMock
from networking import Networking
from networking import inv_typemap
from networking import Connection
from bitcoin import net
from bitcoin import messages
from bitcoin import core
from chain import Block
from chain import BlockOrigin


class NetworkingTest(unittest.TestCase):

    def setUp(self):
        self.networking = Networking()
        self.connection_private = self.networking.connection_private = MagicMock()
        self.connection_public = self.networking.connection_public = MagicMock()
        self.connection_private.host = ('127.0.0.1', '4444')
        self.connection_public.host = ('127.0.0.1', '4444')

        self.chain = MagicMock()

        self.networking.relay[self.connection_private] = Connection(self.connection_public)
        self.networking.relay[self.connection_public] = Connection(self.connection_private)
        self.networking.chain = self.chain

    def test_process_inv_msg_block_private_unknown(self):
        inv = net.CInv()
        inv.hash = 'hash1'
        inv.type = inv_typemap['Block']
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connection_private, msg)

        self.assertFalse(self.connection_public.send.called)
        self.assertTrue(self.connection_private.send.called)
        self.assertEqual(self.connection_private.send.call_args[0][0], 'getdata')

    def test_process_inv_msg_block_public_unknown(self):
        inv = net.CInv()
        inv.hash = 'hash1'
        inv.type = inv_typemap['Block']
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connection_public, msg)

        self.assertFalse(self.connection_private.send.called)
        self.assertTrue(self.connection_public.send.called)
        self.assertEqual(self.connection_public.send.call_args[0][0], 'getdata')

    def test_process_inv_msg_block_known_transfer_unallowed(self):
        inv = net.CInv()
        inv.hash = 'hash1'
        inv.type = inv_typemap['Block']
        msg = messages.msg_inv
        msg.inv = [inv]

        self.chain.blocks = {inv.hash: Block(inv.hash, None, None)}
        self.networking.process_inv(self.connection_public, msg)

        self.assertFalse(self.connection_private.send.called)
        self.assertFalse(self.connection_public.send.called)
        self.assertFalse(self.chain.process_inv.called)

    def test_process_inv_msg_public_block_known_transfer_allowed(self):
        inv = net.CInv()
        inv.hash = 'hash1'
        inv.type = inv_typemap['Block']
        msg = messages.msg_inv
        msg.inv = [inv]

        block = Block(inv.hash, None, None)
        block.transfer_allowed = True

        self.chain.blocks = {inv.hash: block}
        self.networking.process_inv(self.connection_public, msg)

        self.assertFalse(self.chain.process_inv.called)
        self.assertFalse(self.connection_public.send.called)
        self.assertTrue(self.networking.connection_private.send.called)
        self.assertEqual(self.networking.connection_private.send.call_args[0][0], 'inv')
        self.assertEqual(self.networking.connection_private.send.call_args[0][1].inv[0], inv)

    def test_process_inv_msg_private_block_known_transfer_allowed(self):
        inv = net.CInv()
        inv.hash = 'hash1'
        inv.type = inv_typemap['Block']
        msg = messages.msg_inv
        msg.inv = [inv]

        block = Block(inv.hash, None, None)
        block.transfer_allowed = True

        self.chain.blocks = {inv.hash: block}
        self.networking.process_inv(self.connection_private, msg)

        self.assertFalse(self.chain.process_inv.called)
        self.assertFalse(self.connection_private.send.called)
        self.assertTrue(self.networking.connection_public.send.called)
        self.assertEqual(self.networking.connection_public.send.call_args[0][0], 'inv')
        self.assertEqual(self.networking.connection_public.send.call_args[0][1].inv[0], inv)

    def test_process_inv_msg_filtered_block(self):
        inv = net.CInv()
        inv.type = inv_typemap['FilteredBlock']
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connection_private, msg)

        self.assertFalse(self.connection_private.send.called)
        self.assertFalse(self.connection_public.send.called)

    def test_process_inv_msg_error(self):
        inv = net.CInv()
        inv.type = inv_typemap['Error']
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connection_private, msg)

        self.assertFalse(self.connection_private.send.called)
        self.assertTrue(self.connection_public.send.called)
        self.assertEqual(self.connection_public.send.call_args[0][0], 'inv')

        self.assertEqual(len(self.connection_public.send.call_args[0][1].inv), 1)

    def test_process_inv_msg_tx(self):
        inv = net.CInv()
        inv.type = inv_typemap['TX']
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connection_private, msg)

        self.assertFalse(self.connection_private.send.called)
        self.assertTrue(self.connection_public.send.called)
        self.assertEqual(self.connection_public.send.call_args[0][0], 'inv')

        self.assertEqual(len(self.connection_public.send.call_args[0][1].inv), 1)

    def test_process_inv_msg_allowed_block_and_tx(self):
        block = net.CInv()
        block.hash = 'hash1'
        block.type = inv_typemap['Block']
        tx = net.CInv()
        tx.type = inv_typemap['TX']
        msg = messages.msg_inv
        msg.inv = [block, tx]

        block = Block(block.hash, None, None)
        block.transfer_allowed = True

        self.chain.blocks = {block.hash: block}
        self.networking.process_inv(self.connection_public, msg)

        self.assertFalse(self.connection_public.send.called)
        self.assertTrue(self.networking.connection_private.send.called)
        self.assertEqual(len(self.networking.connection_private.send.call_args[0][1].inv), 2)

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

    def test_process_block_unknown(self):
        msg = messages.msg_block
        self.networking.process_block(self.connection_private, msg)

        self.assertTrue(self.chain.process_block.called)

    def test_process_block_known_transfer_unallowed(self):
        cBlock = core.CBlock()
        msg = messages.msg_block
        msg.block = cBlock

        block = Block(cBlock.GetHash(), None, None)
        block.transfer_allowed = False
        self.chain.blocks = {block.hash: block}

        self.networking.process_block(self.connection_private, msg)

        self.assertFalse(self.chain.process_block.called)
        self.assertFalse(self.connection_private.send.called)
        self.assertFalse(self.connection_public.send.called)

    def test_process_block_known_transfer_allowed(self):
        cBlock = core.CBlock()
        msg = messages.msg_block
        msg.block = cBlock

        block = Block(cBlock.GetHash(), None, None)
        block.transfer_allowed = True
        self.chain.blocks = {block.hash: block}

        self.networking.process_block(self.connection_private, msg)

        self.assertFalse(self.chain.process_block.called)
        self.assertFalse(self.connection_private.send.called)
        self.assertTrue(self.connection_public.send.called)

    def test_send_inv_private_blocks(self):
        block1 = Block("hash1", None, BlockOrigin.private)
        block2 = Block("hash2", None, BlockOrigin.private)
        self.networking.send_inv([block1, block2])

        self.assertTrue(self.networking.connection_public.send.called)
        inv_msg = self.networking.connection_public.send.call_args[0][1]
        self.assertEqual(len(inv_msg), 2)

        self.assertFalse(self.networking.connection_private.send.called)

    def test_send_inv_public_blocks(self):
        block1 = Block("hash1", None, BlockOrigin.public)
        block2 = Block("hash2", None, BlockOrigin.public)
        self.networking.send_inv([block1, block2])

        self.assertFalse(self.connection_public.send.called)

        self.assertTrue(self.connection_private.send.called)
        inv_msg = self.networking.connection_private.send.call_args[0][1]
        self.assertEqual(len(inv_msg), 2)

    def test_send_inv_blocks(self):
        block1 = Block("hash1", None, BlockOrigin.public)
        block2 = Block("hash2", None, BlockOrigin.public)
        block3 = Block("hash3", None, BlockOrigin.public)
        block4 = Block("hash4", None, BlockOrigin.private)
        block5 = Block("hash5", None, BlockOrigin.private)
        self.networking.send_inv([block1, block2, block3, block4, block5])

        self.assertTrue(self.connection_public.send.called)
        inv_msg = self.networking.connection_private.send.call_args[0][1]
        self.assertEqual(len(inv_msg), 3)

        self.assertTrue(self.connection_public.send.called)
        inv_msg = self.networking.connection_public.send.call_args[0][1]
        self.assertEqual(len(inv_msg), 2)

    def test_receive_alert(self):
        self.networking.ignore_message(self.connection_public, None)

        self.assertFalse(self.connection_public.send.called)
        self.assertFalse(self.connection_private.send.called)

    def test_receive_get_headers(self):
        self.networking.get_headers_message(self.connection_public, messages.msg_getheaders)
        self.assertFalse(self.connection_private.send.called)

        self.networking.get_headers_message(self.connection_public, messages.msg_getheaders)
        self.assertTrue(self.connection_private.send.called)

        self.assertFalse(self.connection_public.send.called)
