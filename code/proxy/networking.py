from bitcoinnetwork import network
import logging
from chain import Chain
from bitcoin import net
from bitcoin import messages


class Networking(object):
    def __init__(self):
        self.relay = {}

    def start(self):
        client = network.GeventNetworkClient()
        chain = Chain()

        for message in ['notfound', 'addr', 'tx', 'getblocks'
                        'reject', 'alert', 'headers', 'getaddr',
                        'getheaders', 'getdata', 'mempool']:
            client.register_handler(message, self.relay_message)

        client.register_handler('ping', self.ping_message)

        client.register_handler('inv', self.process_inv)
        client.register_handler('block', self.process_block)

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

    def process_inv(self, connection, message):
        relay_inv = []
        for inv in message.inv:
            try:
                if net.CInv.typemap[inv.type] == "Error" or net.CInv.typemap[inv.type] == "TX":
                    relay_inv.append(inv)
                elif net.CInv.typemap[inv.type] == "Block":
                    data_packet = messages.msg_getdata()
                    data_packet.inv.append(message.inv[0])
                    connection.send('getdata', data_packet)
                elif net.CInv.typemap[inv.type] == "FilteredBlock":
                    logging.debug("we don't care about filtered blocks")
                else:
                    logging.debug("unknown inv type")
            except KeyError:
                logging.warn("unknown inv type")

    def process_block(self, connection, message):
        return


if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)
    Networking().start()
