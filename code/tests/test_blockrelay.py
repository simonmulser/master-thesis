import unittest
from mock import MagicMock
from bitcoin import messages
from blockrelay import BlockRelay


class BlockRelayTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(BlockRelayTest, self).__init__(*args, **kwargs)

        self.block_relay = None
        self.networking = None
        self.representative_connection = None
        self.connection = None

    def setUp(self):
        self.networking = MagicMock()
        self.block_relay = BlockRelay(self.networking, [])
        representative_conn = self.representative_connection = self.block_relay.representative_connection = MagicMock()
        connection = self.connection = MagicMock()
        self.representative_connection.host = ('127.0.0.1', '1111')
        self.connection.host = ('127.0.0.2', '2222')

        self.block_relay.connections = [representative_conn, connection]

    def test_send_inv(self):
        self.block_relay.send_inv('msg')

        self.assertTrue(self.representative_connection.send.called)
        self.assertTrue(self.connection.send.called)

    def test_relay_message_normal_connection(self):
        msg = messages.msg_getdata()
        self.block_relay.relay_message(self.connection, msg)

        self.assertFalse(self.connection.send.called)
        self.assertFalse(self.representative_connection.send.called)
        self.assertFalse(self.networking.connection_private.send.called)

    def test_relay_message_representative_connection(self):
        msg = messages.msg_getdata()
        self.block_relay.relay_message(self.representative_connection, msg)

        self.assertFalse(self.connection.send.called)
        self.assertFalse(self.representative_connection.send.called)
        self.assertTrue(self.networking.connection_private.send.called)

    def test_relay_message_private_connection(self):
        msg = messages.msg_getdata()
        self.block_relay.relay_message(self.networking.connection_private, msg)

        self.assertTrue(self.connection.send.called)
        self.assertTrue(self.representative_connection.send.called)
        self.assertFalse(self.networking.connection_private.send.called)