from bitcoinnetwork import network
from bitcoin import core
from bitcoin import messages
import logging


class ClientBehaviourWithCatchUp(network.ClientBehavior):
    def __init__(self, network_client, catch_up_connection):
        super(ClientBehaviourWithCatchUp, self).__init__(network_client)

        self.catch_up_connection = catch_up_connection

    def on_version(self, connection, unused_message):
        if connection.incoming:
            self.send_version(connection)
            self.send_verack(connection)

        else:
            self.send_verack(connection)

        logging.debug('check if connection={} is catch_up_connection={}'
                      .format(connection.host[0], self.catch_up_connection))
        if connection.host[0] == self.catch_up_connection:
            get_headers = messages.msg_getheaders()
            get_headers.locator = messages.CBlockLocator()
            get_headers.locator.vHave = [core.CoreRegTestParams.GENESIS_BLOCK.GetHash()]
            connection.send('getheaders', get_headers)
            logging.info('sent getheaders with genesis block to={} to catch up with chain'.format(connection.host[0]))
