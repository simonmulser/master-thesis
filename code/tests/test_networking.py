import unittest
from mock import MagicMock
from mock import patch
from networking import Networking
import networking
from bitcoin import net
from bitcoin import messages
from bitcoin.core import CBlockHeader
from bitcoin.core import CBlock
from bitcoin.core import CTransaction
from bitcoin.core import CTxIn
from bitcoin.core import COutPoint
from bitcoin.net import CInv
from chain import Block
from chain import BlockOrigin


class NetworkingTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(NetworkingTest, self).__init__(*args, **kwargs)

        self.networking = None
        self.client = None

        self.private_connection = None
        self.public_connections = None
        self.public_connection1 = None
        self.public_connection2 = None

        self.chain = None

    def setUp(self):
        self.networking = Networking('127.0.0.1', MagicMock(), 0)
        self.client = MagicMock()
        self.networking.client = self.client

        self.private_connection = MagicMock()
        self.private_connection.host = ('127.0.0.1', '4444')
        self.public_connection1 = MagicMock()
        self.public_connection1.host = ('public_conn1', '1')
        self.public_connection2 = MagicMock()
        self.public_connection2.host = ('public_conn2', '2')

        self.client.connections = {
            '127.0.0.1': self.private_connection,
            'public_conn1': self.public_connection1,
            'public_conn2': self.public_connection2,

        }

        self.chain = self.networking.chain = MagicMock()

    @patch('chainutil.calc_get_headers')
    def test_inv_message_msg_block_private_unknown_with_tips(self, mock):
        mock.return_value = ['hash20', 'hash19']

        inv = net.CInv()
        inv.hash = 'hash1'
        inv.type = networking.inv_typemap['Block']
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.inv_message(self.private_connection, msg)

        self.assertEqual(self.private_connection.send.call_count, 1)
        self.assertTrue(mock.called)
        self.assertEqual(self.private_connection.send.call_args_list[0][0][0], 'getheaders')

    def test_inv_message_msg_block_known_transfer_unallowed(self):
        inv = net.CInv()
        inv.hash = 'hash1'
        inv.type = networking.inv_typemap['Block']
        msg = messages.msg_inv
        msg.inv = [inv]

        block = Block(None, None)
        block.cached_hash = 'hash1'
        self.chain.blocks = {inv.hash: block}
        self.networking.inv_message(self.public_connection1, msg)

        self.assertFalse(self.private_connection.send.called)
        self.assertFalse(self.public_connection1.send.called)
        self.assertFalse(self.public_connection2.send.called)
        self.assertFalse(self.chain.inv_message.called)

    def test_inv_message_msg_filtered_block(self):
        inv = net.CInv()
        inv.type = networking.inv_typemap['FilteredBlock']
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.inv_message(self.private_connection, msg)

        self.assertFalse(self.private_connection.send.called)
        self.assertFalse(self.public_connection1.send.called)
        self.assertFalse(self.public_connection2.send.called)

    def test_inv_message_msg_error(self):
        inv = net.CInv()
        inv.type = networking.inv_typemap['Error']
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.inv_message(self.private_connection, msg)

        self.assertFalse(self.private_connection.send.called)
        self.assertFalse(self.public_connection1.send.called)
        self.assertFalse(self.public_connection2.send.called)

    def test_inv_message_msg_tx_known(self):
        inv = net.CInv()
        inv.type = networking.inv_typemap['TX']
        inv.hash = 'hash1'
        msg = messages.msg_inv()
        msg.inv = [inv]
        self.networking.txs = {inv.hash: 'saved_transaction'}

        self.networking.inv_message(self.private_connection, msg)

        self.assertFalse(self.private_connection.send.called)
        self.assertFalse(self.public_connection1.send.called)
        self.assertFalse(self.public_connection2.send.called)

    def test_inv_message_msg_unknown(self):
        inv = net.CInv()
        inv.type = "Unknown"
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.inv_message(self.private_connection, msg)

        self.assertFalse(self.private_connection.send.called)
        self.assertFalse(self.public_connection1.send.called)
        self.assertFalse(self.public_connection2.send.called)

    def test_try_to_send_inv_two_blocks_with_cblock(self):
        block1 = Block(None, BlockOrigin.private)
        block1.cblock = MagicMock()
        block2 = Block(None, BlockOrigin.private)
        block2.cblock = MagicMock()

        self.networking.send_inv = MagicMock()

        self.networking.try_to_send_inv([block1, block2])

        self.assertEqual(self.networking.send_inv.call_count, 1)
        self.assertEqual(self.networking.send_inv.call_args[0][0], [block1, block2])

    def test_try_to_send_inv_block_without_cblock(self):
        block1 = Block(None, BlockOrigin.private)
        block1.cached_hash = 'hash1'
        block2 = Block(None, BlockOrigin.private)
        block2.cached_hash = 'hash2'

        self.networking.send_inv = MagicMock()

        self.networking.try_to_send_inv([block1, block2])

        self.assertEqual(self.networking.send_inv.call_count, 1)
        self.assertEqual(self.networking.send_inv.call_args[0][0], [])

        self.assertEqual(len(self.networking.blocks_to_send), 2)
        self.assertEqual(self.networking.blocks_to_send, ['hash1', 'hash2'])

    def test_send_inv_private_blocks(self):
        block1 = Block(None, BlockOrigin.private)
        block1.cached_hash = 'hash1'
        block2 = Block(None, BlockOrigin.private)
        block2.cached_hash = 'hash2'
        self.networking.send_inv([block1, block2])

        self.assertTrue(self.public_connection1.send.called)
        self.assertTrue(self.public_connection2.send.called)
        self.assertEqual(len(self.public_connection2.send.call_args[0][1].inv), 2)

        self.assertFalse(self.private_connection.send.called)

    def test_send_inv_public_blocks(self):
        block1 = Block(None, BlockOrigin.public)
        block1.cached_hash = 'hash1'
        block2 = Block(None, BlockOrigin.public)
        block2.cached_hash = 'hash2'
        self.networking.send_inv([block1, block2])

        self.assertFalse(self.public_connection1.send.called)
        self.assertFalse(self.public_connection2.send.called)

        self.assertTrue(self.private_connection.send.called)
        inv = self.private_connection.send.call_args[0][1].inv
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

        self.assertTrue(self.private_connection.send.called)
        inv = self.private_connection.send.call_args[0][1].inv
        self.assertEqual(len(inv), 3)

        self.assertTrue(self.public_connection1.send.called)
        self.assertTrue(self.public_connection2.send.called)
        self.assertEqual(len(self.public_connection2.send.call_args[0][1].inv), 2)

    def test_ignore_message(self):
        self.networking.ignore_message(self.private_connection, None)

        self.assertFalse(self.private_connection.send.called)
        self.assertFalse(self.public_connection1.send.called)
        self.assertFalse(self.public_connection2.send.called)

    def test_headers_message_known_blocks(self):
        header1 = CBlockHeader(nNonce=1)
        block1 = Block(header1, None)

        header2 = CBlockHeader(nNonce=2)
        block2 = Block(header2, None)

        self.chain.blocks = {block1.hash(): block1, block2.hash(): block2}

        message = messages.msg_headers()
        message.headers = [header1, header2]
        self.networking.headers_message(self.public_connection1, message)

        self.assertFalse(self.public_connection1.send.called)
        self.assertFalse(self.chain.process_block.called)
        self.assertFalse(self.private_connection.send.called)

    def test_headers_message_two_unknown_blocks(self):
        header1 = CBlockHeader(nNonce=1)
        header2 = CBlockHeader(nNonce=2)

        message = messages.msg_headers()
        message.headers = [header1, header2]
        self.networking.headers_message(self.private_connection, message)

        self.assertFalse(self.public_connection1.send.called)
        self.assertFalse(self.public_connection2.send.called)
        self.assertTrue(self.private_connection.send.called)
        self.assertEqual(self.private_connection.send.call_args[0][0], 'getdata')
        self.assertEqual(len(self.private_connection.send.call_args[0][1].inv), 2)
        self.assertEqual(self.chain.process_block.call_count, 2)
        self.assertEqual(self.chain.process_block.call_args[0][1], BlockOrigin.private)

    def test_headers_message_unknown_blocks(self):
        header = CBlockHeader(nNonce=1)

        message = messages.msg_headers()
        message.headers = [header]
        self.networking.headers_message(self.public_connection1, message)

        self.assertTrue(self.public_connection1.send.called)
        self.assertEqual(self.public_connection1.send.call_args[0][0], 'getdata')
        self.assertEqual(self.public_connection1.send.call_args[0][1].inv[0].type, networking.inv_typemap['Block'])
        self.assertEqual(self.public_connection1.send.call_args[0][1].inv[0].hash, header.GetHash())
        self.assertTrue(self.chain.process_block.called)
        self.assertEqual(self.chain.process_block.call_args[0][1], BlockOrigin.public)

    @patch('chainutil.get_headers')
    def test_getheaders_message_no_blocks_to_return(self, mock):
        message = messages.msg_getheaders()
        message.locator.vHave = ['hash1']
        self.chain.tips = {'some_hash': 'some_block'}
        mock.return_value = []

        self.networking.getheaders_message(self.private_connection, message)

        self.assertTrue(mock.called)
        self.assertEqual(mock.call_args[0][0], self.chain.tips)
        self.assertEqual(mock.call_args[0][1], BlockOrigin.private)
        self.assertEqual(mock.call_args[0][2], message.locator.vHave)
        self.assertTrue(self.private_connection.send.called)
        self.assertEqual(self.private_connection.send.call_args[0][0], 'headers')
        self.assertEqual(self.private_connection.send.call_args[0][1].headers, [])

    @patch('chainutil.get_headers')
    def test_getheaders_message_no_block_found(self, mock):
        message = messages.msg_getheaders()
        block1 = Block('cblock_header1', BlockOrigin.private)
        block1.cblock = CBlock(nNonce=1)
        block2 = Block('cblock_header2', BlockOrigin.private)
        block2.cblock = CBlock(nNonce=2)
        mock.return_value = [block1, block2]

        self.networking.getheaders_message(self.private_connection, message)

        self.assertTrue(self.private_connection.send.called)
        self.assertEqual(len(self.private_connection.send.call_args[0][1].headers), 2)
        self.assertEqual(self.private_connection.send.call_args[0][1].headers[0], block1.cblock)
        self.assertEqual(self.private_connection.send.call_args[0][1].headers[1], block2.cblock)

    def test_block_message(self):
        message = messages.msg_block()
        cblock = CBlock()
        message.block = cblock

        block = Block(None, BlockOrigin.private)
        block.cached_hash = message.block.GetHash()

        self.chain.blocks = {block.hash():  block}

        self.networking.block_message(self.private_connection, message)

        self.assertEqual(self.chain.blocks[block.hash()].cblock, cblock)

    def test_block_message_with_block_to_send(self):
        message = messages.msg_block()
        cblock = CBlock()
        message.block = cblock

        block = Block(None, BlockOrigin.private)
        block.cached_hash = message.block.GetHash()

        self.chain.blocks = {block.hash():  block}
        self.networking.send_inv = MagicMock()
        self.networking.blocks_to_send = [block.hash()]

        self.networking.block_message(self.private_connection, message)

        self.assertTrue(self.networking.send_inv.called)
        self.assertEqual(self.networking.send_inv.call_args[0][0], [block])
        self.assertEqual(len(self.networking.blocks_to_send), 0)

    def test_block_message_two_times(self):
        message = messages.msg_block()
        cblock1 = CBlock(nNonce=1)
        cblock2 = CBlock(nNonce=2)
        message.block = cblock1

        block = Block(None, BlockOrigin.private)
        block.cached_hash = message.block.GetHash()

        self.chain.blocks = {block.hash():  block}

        self.networking.block_message(self.private_connection, message)
        message.block = cblock2
        self.networking.block_message(self.private_connection, message)

        self.assertEqual(self.chain.blocks[block.hash()].cblock, cblock1)

    def test_getdata_message_with_block(self):
        cblock = CBlock()
        block = Block(cblock, BlockOrigin.private)
        block.cblock = cblock
        message = messages.msg_getdata()
        cInv = CInv()
        cInv.type = networking.inv_typemap['Block']
        cInv.hash = cblock.GetHash()
        message.inv = [cInv]

        self.chain.blocks = {cblock.GetHash(): block}

        self.networking.getdata_message(self.public_connection1, message)

        self.assertTrue(self.public_connection1.send.called)
        self.assertEqual(self.public_connection1.send.call_args[0][0], 'block')
        self.assertEqual(self.public_connection1.send.call_args[0][1].block, cblock)

    def test_getdata_message_cblock_not_available(self):
        cblock = CBlock()
        block = Block(cblock, BlockOrigin.private)
        message = messages.msg_getdata()
        cInv = CInv()
        cInv.type = networking.inv_typemap['Block']
        cInv.hash = cblock.GetHash()
        message.inv = [cInv]

        self.chain.blocks = {cblock.GetHash(): block}

        self.networking.getdata_message(self.public_connection1, message)

        self.assertFalse(self.public_connection1.called)

    def test_getdata_message_with_unknown_hashes(self):
        message = messages.msg_getdata()
        cInv1 = CInv()
        cInv1.type = networking.inv_typemap['Block']
        cInv1.hash = 'hash1'
        cInv2 = CInv()
        cInv2.type = networking.inv_typemap['Block']
        cInv2.hash = 'hash2'
        message.inv = [cInv1, cInv2]

        self.chain.blocks = {}

        self.networking.getdata_message(self.public_connection1, message)

        self.assertFalse(self.public_connection1.send.called)

    def test_getdata_message_with_two_blocks(self):
        cblock1 = CBlock()
        block1 = Block(cblock1, BlockOrigin.private)
        block1.cblock = cblock1
        cInv1 = CInv()
        cInv1.type = networking.inv_typemap['Block']
        cInv1.hash = cblock1.GetHash()
        cblock2 = CBlock()
        block2 = Block(cblock2, BlockOrigin.private)
        block2.cblock = cblock2
        cInv2 = CInv()
        cInv2.type = networking.inv_typemap['Block']
        cInv2.hash = cblock2.GetHash()
        message = messages.msg_getdata()
        message.inv = [cInv1, cInv2]

        self.chain.blocks = {cblock1.GetHash(): block1, cblock2.GetHash(): block2}

        self.networking.getdata_message(self.public_connection1, message)

        self.assertTrue(self.public_connection1.send.called)
        self.assertEqual(self.public_connection1.send.call_count, 2)

    def test_getdata_message_without_tx(self):
        message = messages.msg_getdata()
        inv = CInv()
        inv.type = networking.inv_typemap['TX']
        inv.hash = 'hash1'
        message.inv = [inv]

        self.networking.get_tx = MagicMock()
        self.networking.get_tx.return_value = None

        self.networking.getdata_message(self.public_connection1, message)

        self.assertFalse(self.private_connection.send.called)
        self.assertFalse(self.public_connection1.send.called)
        self.assertFalse(self.public_connection2.send.called)

    def test_get_private_connection(self):
        connection = self.networking.get_private_connection()

        self.assertEqual(connection, self.private_connection)

    def test_get_private_connection_no_pirvate_connection(self):
        del self.client.connections['127.0.0.1']

        connection = self.networking.get_private_connection()

        self.assertEqual(connection, None)

    def test_get_current_public_connection(self):
        connections = list(self.networking.get_current_public_connection())

        self.assertEqual(len(connections), 2)
