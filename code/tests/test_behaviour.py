from mock import MagicMock
from behaviour import ClientBehaviourWithCatchUp
import unittest


class BehaviourTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(BehaviourTest, self).__init__(*args, **kwargs)
        self.client = None
        self.ip = None
        self.behaviour = None

    def setUp(self):
        self.client = MagicMock()
        self.ip = '127.0.0.1'
        self.behaviour = ClientBehaviourWithCatchUp(self.client, self.ip)

    def test_on_version_connection_matches_catch_up_connection(self):
        super(BehaviourTest, self).setUp()
        connection = MagicMock()
        connection.host = (self.ip, '1234')

        self.behaviour.on_version(connection, None)

        self.assertTrue(connection.send.called)
        self.assertTrue(connection.send.call_count, 3)
        self.assertEqual(connection.send.call_args_list[-1][0][0], 'getheaders')

    def test_on_version_connection_do_not_matches(self):
        super(BehaviourTest, self).setUp()
        connection = MagicMock()
        connection.host = ('1.1.1.1', '1234')

        self.behaviour.on_version(connection, None)

        self.assertTrue(connection.send.called)
        self.assertTrue(connection.send.call_count, 2)
        self.assertNotEqual(connection.send.call_args_list[-1][0][0], 'getheaders')


