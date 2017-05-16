from bitcoinnetwork import network
import logging
from bitcoin import net
from bitcoin import messages
from strategy import BlockOrigin
from threading import Lock
import chain
from threading import Thread


class BlockRelay(object):

    def __init__(self, networking, ips):
        self.networking = networking
        self.ips = ips
        self.connections = []
        self.representative_connection = None

    def start(self):
        logging.debug('starting block relay client')

        client = network.GeventNetworkClient()

        for message in ['getdata', 'getheaders', 'block', 'headers']:
            client.register_handler(message, self.relay_message)

        client.register_handler('ping', self.ping_message)
        network.ClientBehavior(client)

        for ip in self.ips:
            connection = client.connect((ip, 18444))
            self.connections.append(connection)
        if len(self.connections) > 0:
            self.representative_connection = self.connections[0]

        client.run_forever()

    def send_inv(self, msg):
        for connection in self.connections:
            connection.send('inv', msg)
        logging.info('relayed inv message to to all connections')

    def relay_message(self, connection, message):
        if connection is self.representative_connection:
            self.networking.connection_private.send(message.command, message)
            logging.info('relayed message={} from {} to private-alice'.format(connection.host[0], message.command))
        elif connection is self.networking.connection_private:
            for connection in self.connections:
                connection.send(message.command, message)
            logging.info('relayed message={} from private-alice to to all connections'.format(message.command))

    def ping_message(self, connection, message):
        connection.send('pong', message)
