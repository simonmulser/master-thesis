from bitcoinnetwork import network
import logging
from selfishlogic import SelfishLogic


class Networking(object):
    def __init__(self):
        self.relay = {}

    def start(self):
        client = network.GeventNetworkClient()
        selfish_logic = SelfishLogic()

        for message in ['notfound', 'addr', 'tx', 'getblocks'
                        'reject', 'alert', 'headers', 'getaddr',
                        'getheaders', 'getdata', 'mempool']:
            client.register_handler(message, self.relay_message)

        client.register_handler('ping', self.ping_message)

        client.register_handler('inv', selfish_logic.process_inv_msg)
        client.register_handler('block', selfish_logic.process_block)

        network.ClientBehavior(client)

        alice = client.connect(('240.0.0.2', 18444))
        bob = client.connect(('240.0.0.3', 18444))

        self.relay[alice] = bob
        self.relay[bob] = alice

        client.run_forever()

    def relay_message(self, connection, message):
        logging.debug('relaying %s message from %s:%d', message.command, *connection.host)

        while self.relay[connection] is None:
            logging.debug('wait for second client to connect')
            sleep(1)
        relay_connection = self.relay[connection]

        #relay_connection.send(message.command, message)

    def ping_message(self, connection, message):
        print connection
        connection.send('pong', message)


if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)
    Networking().start()
