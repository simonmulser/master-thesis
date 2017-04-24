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
        self.chain = MagicMock()

        self.networking.relay[self.connectionAlice] = self.connectionBob
        self.networking.relay[self.connectionBob] = self.connectionAlice
        self.networking.chain = self.chain

    def test_process_inv_msg_block(self):
        inv = net.CInv()
        inv.type = get_type_key("Block")
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connectionAlice, msg)

        self.assertTrue(self.connectionAlice.send.called)
        self.assertEqual(self.connectionAlice.send.call_args[0][0], 'getdata')
        self.assertFalse(self.connectionBob.send.called)

    def test_process_inv_msg_filtered_block(self):
        inv = net.CInv()
        inv.type = get_type_key("FilteredBlock")
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connectionAlice, msg)

        self.assertFalse(self.connectionAlice.send.called)
        self.assertFalse(self.connectionBob.send.called)

    def test_process_inv_msg_error(self):
        inv = net.CInv()
        inv.type = get_type_key("Error")
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connectionAlice, msg)

        self.assertFalse(self.connectionAlice.send.called)
        self.assertTrue(self.connectionBob.send.called)
        self.assertEqual(self.connectionBob.send.call_args[0][0], 'inv')

        amount_of_inv = len(self.connectionBob.send.call_args[0][1])
        self.assertEqual(amount_of_inv, 1)

    def test_process_inv_msg_tx(self):
        inv = net.CInv()
        inv.type = get_type_key("TX")
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connectionAlice, msg)

        self.assertFalse(self.connectionAlice.send.called)
        self.assertTrue(self.connectionBob.send.called)
        self.assertEqual(self.connectionBob.send.call_args[0][0], 'inv')

        amount_of_inv = len(self.connectionBob.send.call_args[0][1])
        self.assertEqual(amount_of_inv, 1)

    def test_process_inv_msg_unknown(self):
        inv = net.CInv()
        inv.type = "Unknown"
        msg = messages.msg_inv
        msg.inv = [inv]
        self.networking.process_inv(self.connectionAlice, msg)

        self.assertFalse(self.connectionAlice.send.called)
        self.assertFalse(self.connectionBob.send.called)

    def test_relay_message(self):
        msg = messages.msg_version
        self.networking.relay_message(self.connectionAlice, msg)

        self.assertFalse(self.connectionAlice.send.called)
        self.assertTrue(self.connectionBob.send.called)
        self.assertEqual(self.connectionBob.send.call_args[0][0], msg.command)

    def test_process_block(self):
        msg = messages.msg_version
        self.networking.process_block(self.connectionAlice, msg)

        self.assertTrue(self.chain.process_block.called)


def get_type_key(msg_type):
    for key in net.CInv.typemap.keys():
        if net.CInv.typemap[key] == msg_type:
            return key
