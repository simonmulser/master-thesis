import sys
sys.path.append('pycoin')
sys.path.append('python-bitcoinlib')

from bitcoinnetwork import network
import logging

class Proxy(object):
    def __init__(self):
        self.relay = {}

    def start(self):
        client = network.GeventNetworkClient()

        #for t in network.messages.parsers:
        client.register_handler('inv', self.relay_message)
        client.register_handler('getheaders', self.test)
        client.register_handler('ping', self.ping_message)

        network.ClientBehavior(client)

        alice = client.connect(('240.0.0.2', 18444))
        bob = client.connect(('240.0.0.3', 18444))

        self.relay[alice] = bob
        self.relay[bob] = alice

        client.run_forever()

    def test(self, connection, message):

        logging.debug(message.locator)
        logging.debug(message.hashstop)

    def relay_message(self, connection, message):
        logging.debug('relaying %s message from %s:%d', message.type, *connection.host)

        while self.relay[connection] is None:
            logging.debug('wait for second client to connect')
            sleep(1)
        relay_connection = self.relay[connection]
        relay_connection.send(message.command, message)

    def getheaders_message(self, connection, message):
        logging.debug('%s message from %s:%d', message.command, *connection.host)

    def ping_message(self, connection, message):
        logging.debug('%s message from %s:%d', message.command, *connection.host)
        logging.debug(message.command)
        connection.send('pong', message)


if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)
    Proxy().start()
