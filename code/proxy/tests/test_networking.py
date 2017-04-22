import unittest
import mock
from networking import Networking
from bitcoin import net
from bitcoin import messages


class NetworkingTest(unittest.TestCase):

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_inv_msg_block(self, connection):
        networking = Networking()
        inv = net.CInv()
        inv.type = get_type_key("Block")
        msg = messages.msg_inv
        msg.inv = [inv]
        networking.process_inv(connection, msg)

        self.assertTrue(connection.send.called)
        self.assertEqual(connection.send.call_args[0][0], 'getdata')

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_inv_msg_filtered_block(self, connection):
        networking = Networking()
        inv = net.CInv()
        inv.type = get_type_key("FilteredBlock")
        msg = messages.msg_inv
        msg.inv = [inv]
        networking.process_inv(connection, msg)

        self.assertFalse(connection.send.called)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_inv_msg_error(self, connection):
        networking = Networking()
        inv = net.CInv()
        inv.type = get_type_key("Error")
        msg = messages.msg_inv
        msg.inv = [inv]
        networking.process_inv(connection, msg)

        self.assertFalse(connection.send.called)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_inv_msg_tx(self, connection):
        networking = Networking()
        inv = net.CInv()
        inv.type = get_type_key("TX")
        msg = messages.msg_inv
        msg.inv = [inv]
        networking.process_inv(connection, msg)

        self.assertFalse(connection.send.called)

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_inv_msg_error(self, connection):
        networking = Networking()
        inv = net.CInv()
        inv.type = "Unknown"
        msg = messages.msg_inv
        msg.inv = [inv]
        networking.process_inv(connection, msg)

        self.assertFalse(connection.send.called)


def get_type_key(msg_type):
    for key in net.CInv.typemap.keys():
        if net.CInv.typemap[key] == msg_type:
            return key
