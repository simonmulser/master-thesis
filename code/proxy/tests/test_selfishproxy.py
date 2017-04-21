import unittest
import mock
from selfishlogic import SelfishLogic
from bitcoin import net
from bitcoin import messages


class SelfishProxyTest(unittest.TestCase):

    def test_selfishproxy(self):
        assert 1 == 1

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_inv_msg_block(self, connection):
        a = SelfishLogic()
        inv = net.CInv()
        inv.type = get_type_key("Block")
        msg = messages.msg_inv
        msg.inv = [inv]
        a.process_inv_msg(connection, msg)
        assert connection.send.called
        assert connection.send.call_args[0][0] == 'getdata'

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_inv_msg_filtered_block(self, connection):
        a = SelfishLogic()
        inv = net.CInv()
        inv.type = get_type_key("FilteredBlock")
        msg = messages.msg_inv
        msg.inv = [inv]
        a.process_inv_msg(connection, msg)
        assert connection.send.called is False

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_inv_msg_error(self, connection):
        a = SelfishLogic()
        inv = net.CInv()
        inv.type = get_type_key("Error")
        msg = messages.msg_inv
        msg.inv = [inv]
        a.process_inv_msg(connection, msg)
        assert connection.send.called is False

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_inv_msg_tx(self, connection):
        a = SelfishLogic()
        inv = net.CInv()
        inv.type = get_type_key("TX")
        msg = messages.msg_inv
        msg.inv = [inv]
        a.process_inv_msg(connection, msg)
        assert connection.send.called is False

    @mock.patch('bitcoinnetwork.network.GeventConnection', autospec=True)
    def test_process_inv_msg_error(self, connection):
        a = SelfishLogic()
        inv = net.CInv()
        inv.type = "Unknown"
        msg = messages.msg_inv
        msg.inv = [inv]
        a.process_inv_msg(connection, msg)
        assert connection.send.called is False


def get_type_key(msg_type):
    for key in net.CInv.typemap.keys():
        if net.CInv.typemap[key] == msg_type:
            return key
