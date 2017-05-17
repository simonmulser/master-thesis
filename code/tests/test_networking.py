import unittest
from mock import MagicMock
from mock import patch
from networking import Networking
import networking
from networking import Connection
from bitcoin import net
from bitcoin import messages
from bitcoin.core import CBlockHeader
from bitcoin.net import CBlockLocator
from chain import Block
from chain import BlockOrigin


class NetworkingTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(NetworkingTest, self).__init__(*args, **kwargs)

        self.networking = None
        self.connection_private = None
        self.connection_public = None
        self.chain = None
        self.block_relay = None

    def setUp(self):
        self.networking = Networking()
        conn_private = self.connection_private = self.networking.connection_private = MagicMock()
        conn_public = self.connection_public = self.networking.connection_public = MagicMock()
        self.connection_private.host = ('127.0.0.1', '4444')
        self.connection_public.host = ('127.0.0.1', '4444')

        self.chain = self.networking.chain = MagicMock()
        self.block_relay = self.networking.block_relay = MagicMock()

        self.networking.connections = {conn_public: Connection(conn_public, 'alice-public', conn_private),
                                       conn_private: Connection(conn_private, 'alice-private', conn_public)}

    @patch('chain.get_relevant_tips')
    def test_process_inv_msg_block_private_unknown_with_tips(self, mock):
        block = Block(None, "public")
        block.cached_hash = 'a1'
        mock.return_value = [block, block]

        inv = net.CInv()
        inv.hash = 'hash1'
        inv.type = networking.inv_typemap['Block']
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connection_private, msg)

        self.assertEqual(self.connection_private.send.call_count, 2)
        self.assertTrue(mock.called)
        self.assertEqual(self.connection_private.send.call_args_list[0][0][0], 'getheaders')
        self.assertEqual(self.connection_private.send.call_args_list[1][0][0], 'getheaders')

    def test_process_inv_msg_block_known_transfer_unallowed(self):
        inv = net.CInv()
        inv.hash = 'hash1'
        inv.type = networking.inv_typemap['Block']
        msg = messages.msg_inv
        msg.inv = [inv]

        block = Block(None, None)
        block.cached_hash = 'hash1'
        self.chain.blocks = {inv.hash: block}
        self.networking.process_inv(self.connection_public, msg)

        self.assertFalse(self.connection_private.send.called)
        self.assertFalse(self.connection_public.send.called)
        self.assertFalse(self.chain.process_inv.called)

    def test_process_inv_msg_public_block_known_transfer_allowed(self):
        inv = net.CInv()
        inv.hash = 'hash1'
        inv.type = networking.inv_typemap['Block']
        msg = messages.msg_inv
        msg.inv = [inv]

        block = Block(inv.hash, None)
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
        inv.type = networking.inv_typemap['Block']
        msg = messages.msg_inv
        msg.inv = [inv]

        block = Block(inv.hash, None)
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
        inv.type = networking.inv_typemap['FilteredBlock']
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connection_private, msg)

        self.assertFalse(self.connection_private.send.called)
        self.assertFalse(self.connection_public.send.called)

    def test_process_inv_msg_error(self):
        inv = net.CInv()
        inv.type = networking.inv_typemap['Error']
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connection_private, msg)

        self.assertFalse(self.connection_private.send.called)
        self.assertTrue(self.connection_public.send.called)
        self.assertEqual(self.connection_public.send.call_args[0][0], 'inv')

        self.assertEqual(len(self.connection_public.send.call_args[0][1].inv), 1)

    def test_process_inv_msg_tx(self):
        inv = net.CInv()
        inv.type = networking.inv_typemap['TX']
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
        block.type = networking.inv_typemap['Block']
        tx = net.CInv()
        tx.type = networking.inv_typemap['TX']
        msg = messages.msg_inv
        msg.inv = [block, tx]

        block = Block(None, None)
        block.cached_hash = 'hash1'
        block.transfer_allowed = True

        self.chain.blocks = {block.hash(): block}
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

    def test_send_inv_private_blocks(self):
        block1 = Block(None, BlockOrigin.private)
        block1.cached_hash = 'hash1'
        block2 = Block(None, BlockOrigin.private)
        block2.cached_hash = 'hash2'
        self.networking.send_inv([block1, block2])

        self.assertTrue(self.networking.connection_public.send.called)
        self.assertTrue(self.networking.block_relay.send_inv.called)
        inv = self.networking.connection_public.send.call_args[0][1].inv
        self.assertEqual(len(inv), 2)

        self.assertFalse(self.networking.connection_private.send.called)

    def test_send_inv_public_blocks(self):
        block1 = Block(None, BlockOrigin.public)
        block1.cached_hash = 'hash1'
        block2 = Block(None, BlockOrigin.public)
        block2.cached_hash = 'hash2'
        self.networking.send_inv([block1, block2])

        self.assertFalse(self.connection_public.send.called)
        self.assertFalse(self.networking.block_relay.send_inv.called)

        self.assertTrue(self.connection_private.send.called)
        inv = self.networking.connection_private.send.call_args[0][1].inv
        self.assertEqual(len(inv), 2)

    def test_send_inv_blocks(self):
        block1 = Block(None, BlockOrigin.public)
        block1.cached_hash = 'hash1'
        block2 = Block(None, BlockOrigin.public)
        block2.cached_hash = 'hash2'
        block3 = Block(None, BlockOrigin.public)
        block3.cached_hash = 'hash3'
        block4 = Block(None, BlockOrigin.private)
        block4.cached_hash = 'hash4'
        block5 = Block(None, BlockOrigin.private)
        block5.cached_hash = 'hash5'

        self.networking.send_inv([block1, block2, block3, block4, block5])

        self.assertTrue(self.connection_private.send.called)
        inv = self.networking.connection_private.send.call_args[0][1].inv
        self.assertEqual(len(inv), 3)

        self.assertTrue(self.connection_public.send.called)
        inv = self.networking.connection_public.send.call_args[0][1].inv
        self.assertEqual(len(inv), 2)

    def test_ignore_message(self):
        self.networking.ignore_message(self.connection_public, None)

        self.assertFalse(self.connection_public.send.called)
        self.assertFalse(self.connection_private.send.called)

    def test_headers_message_known_blocks(self):
        header1 = CBlockHeader(nNonce=1)
        block1 = Block(header1, None)

        header2 = CBlockHeader(nNonce=2)
        block2 = Block(header2, None)

        self.chain.blocks = {block1.hash(): block1, block2.hash(): block2}

        message = messages.msg_headers()
        message.headers = [header1, header2]
        self.networking.headers_message(self.connection_public, message)

        self.assertFalse(self.connection_public.send.called)
        self.assertFalse(self.chain.process_block.called)
        self.assertFalse(self.connection_private.send.called)

    def test_headers_message_unknown_blocks(self):
        header1 = CBlockHeader(nNonce=1)
        header2 = CBlockHeader(nNonce=2)

        message = messages.msg_headers()
        message.headers = [header1, header2]
        self.networking.headers_message(self.connection_private, message)

        self.assertFalse(self.connection_public.send.called)
        self.assertFalse(self.connection_private.send.called)
        self.assertTrue(self.chain.process_block.called)
        self.assertEqual(self.chain.process_block.call_count, 2)
        self.assertEqual(self.chain.process_block.call_args[0][1], BlockOrigin.private)

    def test_getheaders_message_one_next_block(self):
        message = messages.msg_getheaders()
        message.locator = CBlockLocator()
        message.locator.vHave = ['hash1']

        nextBlock = Block('cblock2', BlockOrigin.private)
        nextBlock.cached_hash = 'hash2'
        nextBlock.transfer_allowed = True
        block = Block(None, BlockOrigin.private)
        block.cached_hash = 'hash1'
        block.nextBlock = nextBlock
        self.chain.blocks = {block.hash(): block, nextBlock.hash(): nextBlock}

        self.networking.getheaders_message(self.connection_private, message)

        self.assertTrue(self.connection_private.send.called)
        self.assertEqual(self.connection_private.send.call_args[0][0], 'headers')
        self.assertEqual(len(self.connection_private.send.call_args[0][1].headers), 1)
        self.assertEqual(self.connection_private.send.call_args[0][1].headers[0], 'cblock2')

    def test_getheaders_message_no_next_block(self):
        message = messages.msg_getheaders()
        message.locator = CBlockLocator()
        message.locator.vHave = ['hash1']

        block = Block(None, BlockOrigin.private)
        block.cached_hash = 'hash1'
        self.chain.blocks = {block.hash(): block}

        self.networking.getheaders_message(self.connection_private, message)

        self.assertTrue(self.connection_private.send.called)
        self.assertEqual(self.connection_private.send.call_args[0][0], 'headers')
        self.assertEqual(len(self.connection_private.send.call_args[0][1].headers), 0)

    def test_getheaders_message_no_block(self):
        message = messages.msg_getheaders()
        message.locator = CBlockLocator()
        message.locator.vHave = ['hash1']

        self.networking.getheaders_message(self.connection_private, message)

        self.assertTrue(self.connection_private.send.called)
        self.assertEqual(self.connection_private.send.call_args[0][0], 'headers')
        self.assertEqual(len(self.connection_private.send.call_args[0][1].headers), 0)

    def test_getheaders_message_two_next_block(self):
        message = messages.msg_getheaders()
        message.locator = CBlockLocator()
        message.locator.vHave = ['hash1']

        nextNextBlock = Block('cblock3', BlockOrigin.private)
        nextNextBlock.cached_hash = 'hash3'
        nextNextBlock.transfer_allowed = True
        nextBlock = Block('cblock2', BlockOrigin.private)
        nextBlock.cached_hash = 'hash2'
        nextBlock.nextBlock = nextNextBlock
        nextBlock.transfer_allowed = True
        block = Block(None, BlockOrigin.private)
        block.cached_hash = 'hash1'
        block.nextBlock = nextBlock
        self.chain.blocks = {block.hash(): block, nextBlock.hash(): nextBlock, nextNextBlock.hash(): nextNextBlock}

        self.networking.getheaders_message(self.connection_private, message)

        self.assertTrue(self.connection_private.send.called)
        self.assertEqual(self.connection_private.send.call_args[0][0], 'headers')
        self.assertEqual(len(self.connection_private.send.call_args[0][1].headers), 2)
        self.assertTrue('cblock3' in self.connection_private.send.call_args[0][1].headers)
        self.assertTrue('cblock2' in self.connection_private.send.call_args[0][1].headers)

    def test_getheaders_message_two_next_block_transfer_not_allowed(self):
        message = messages.msg_getheaders()
        message.locator = CBlockLocator()
        message.locator.vHave = ['hash1']

        nextNextBlock = Block('cblock3', BlockOrigin.private)
        nextNextBlock.cached_hash = 'hash3'
        nextBlock = Block('cblock2', BlockOrigin.private)
        nextBlock.cached_hash = 'hash2'
        nextBlock.nextBlock = nextNextBlock
        nextBlock.transfer_allowed = True
        block = Block(None, BlockOrigin.private)
        block.cached_hash = 'hash1'
        block.nextBlock = nextBlock
        self.chain.blocks = {block.hash(): block, nextBlock.hash(): nextBlock, nextNextBlock.hash(): nextNextBlock}

        self.networking.getheaders_message(self.connection_private, message)

        self.assertTrue(self.connection_private.send.called)
        self.assertEqual(self.connection_private.send.call_args[0][0], 'headers')
        self.assertEqual(len(self.connection_private.send.call_args[0][1].headers), 1)
        self.assertTrue('cblock2' in self.connection_private.send.call_args[0][1].headers)
