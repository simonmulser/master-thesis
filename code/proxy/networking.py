from bitcoinnetwork import network
import logging
from chain import Chain
from bitcoin import net
from bitcoin import messages
from chain import Visibility


class Networking(object):
    def __init__(self):
        self.network_partitions = {}
        self.alice = None
        self.bob = None
        self.chain = Chain()

    def start(self):
        client = network.GeventNetworkClient()

        for message in ['notfound', 'addr', 'tx', 'getblocks'
                        'reject', 'alert', 'headers', 'getaddr',
                        'getheaders', 'getdata', 'mempool']:
            client.register_handler(message, self.relay_message)

        client.register_handler('ping', self.ping_message)

        client.register_handler('inv', self.process_inv)
        client.register_handler('block', self.process_block)

        network.ClientBehavior(client)

        self.alice = client.connect(('240.0.0.2', 18444))
        self.bob = client.connect(('240.0.0.3', 18444))

        partition_alice = NetworkPartition(self.alice, self.bob)
        partition_bob = NetworkPartition(self.bob, self.alice)

        self.network_partitions[self.alice] = partition_alice
        self.network_partitions[self.bob] = partition_bob

        client.run_forever()

    def relay_message(self, connection, message):
        logging.debug('relaying %s message from %s:%d', message.command, *connection.host)

        self.network_partitions[connection].outbound.send(message.command, message)

    def ping_message(self, connection, message):
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

        if len(relay_inv) > 0:
            self.network_partitions[connection].outbound.send('inv', relay_inv)

    def process_block(self, connection, message):
        if connection == self.alice:
            self.chain.process_block(message, Visibility.alice)
        else:
            self.chain.process_block(message, Visibility.public)


class NetworkPartition:

    def __init__(self, inbound, outbound):
        self.inbound = inbound
        self.outbound = outbound


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    Networking().start()
