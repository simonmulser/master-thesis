import unittest
from mock import MagicMock
from networking import Networking
from bitcoin import net
from bitcoin import messages


class NetworkingTest(unittest.TestCase):

    def setUp(self):
        self.networking = Networking()
        self.connectionAlice = MagicMock()
        self.connectionBob = MagicMock()

        self.networking.relay[self.connectionAlice] = self.connectionBob
        self.networking.relay[self.connectionBob] = self.connectionAlice

    def test_process_inv_msg_block(self):
        inv = net.CInv()
        inv.type = get_type_key("Block")
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connectionAlice, msg)

        self.assertTrue(self.connectionAlice.send.called)
        self.assertEqual(self.connectionAlice.send.call_args[0][0], 'getdata')

    def test_process_inv_msg_filtered_block(self):
        inv = net.CInv()
        inv.type = get_type_key("FilteredBlock")
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connectionAlice, msg)

        self.assertFalse(self.connectionAlice.send.called)

    def test_process_inv_msg_error(self):
        inv = net.CInv()
        inv.type = get_type_key("Error")
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connectionAlice, msg)

        self.assertFalse(self.connectionAlice.send.called)

    def test_process_inv_msg_tx(self):
        inv = net.CInv()
        inv.type = get_type_key("TX")
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connectionAlice, msg)

        self.assertFalse(self.connectionAlice.send.called)

    def test_process_inv_msg_error(self):
        inv = net.CInv()
        inv.type = "Unknown"
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connectionAlice, msg)

        self.assertFalse(self.connectionAlice.send.called)


def get_type_key(msg_type):
    for key in net.CInv.typemap.keys():
        if net.CInv.typemap[key] == msg_type:
            return key
