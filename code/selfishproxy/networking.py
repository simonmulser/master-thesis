from bitcoinnetwork import network
import logging
from chain import Chain
from bitcoin import net
from bitcoin import messages
from strategy import BlockOrigin


class Networking(object):
    def __init__(self):
        self.relay = {}
        self.connection_private = None
        self.connection_public = None
        self.chain = Chain(self)

    def start(self):
        client = network.GeventNetworkClient()

        for message in ['notfound', 'addr', 'tx', 'getblocks'
                        'reject', 'headers', 'getaddr',
                        'getdata', 'mempool']:
            client.register_handler(message, self.relay_message)

        client.register_handler('ping', self.ping_message)
        client.register_handler('alert', self.alert_message)
        client.register_handler('getheaders', self.get_headers_message)

        client.register_handler('inv', self.process_inv)
        client.register_handler('block', self.process_block)

        network.ClientBehavior(client)

        self.connection_private = client.connect(('240.0.0.2', 18444))
        self.connection_public = client.connect(('240.0.0.3', 18444))

        self.relay[self.connection_private] = Connection(self.connection_public)
        self.relay[self.connection_public] = Connection(self.connection_private)

        client.run_forever()
        logging.debug('client started')

    def relay_message(self, connection, message):
        self.relay[connection].connection.send(message.command, message)
        logging.debug('relayed {} message from {}'.format(message.command, connection.host[0]))

    def process_inv(self, connection, message):
        logging.debug('received inv from {}'.format(connection.host[0]))

        relay_inv = []
        for inv in message.inv:
            try:
                if net.CInv.typemap[inv.type] == "Error" or net.CInv.typemap[inv.type] == "TX":
                    relay_inv.append(inv)
                elif net.CInv.typemap[inv.type] == "Block":
                    if inv.hash in self.chain.blocks:
                        if self.chain.blocks[inv.hash].transfer_allowed:
                            relay_inv.append(inv)
                    else:
                        data_packet = messages.msg_getdata()
                        data_packet.inv.append(message.inv[0])
                        connection.send('getdata', data_packet)

                        logging.info('requested new block from {}'.format(connection.host[0]))
                elif net.CInv.typemap[inv.type] == "FilteredBlock":
                    logging.debug("we don't care about filtered blocks")
                else:
                    logging.debug("unknown inv type")
            except KeyError:
                logging.warn("unknown inv type")

        if len(relay_inv) > 0:
            message.inv = relay_inv
            self.relay_message(connection, message)

    def process_block(self, connection, message):
        logging.info('received block from {}'.format(connection.host[0]))

        block = message.block
        if block.GetHash() in self.chain.blocks:
            if self.chain.blocks[block.GetHash()].transfer_allowed:
                self.relay_message(connection, message)
        else:
            if connection == self.connection_private:
                self.chain.process_block(block, BlockOrigin.private)
            else:
                self.chain.process_block(block, BlockOrigin.public)

    def send_inv(self, blocks):
        private_block_invs = []
        public_block_invs = []

        for block in blocks:
            inv = net.CInv()
            inv.type = inv_typemap['Block']
            inv.hash = block.hash

            if block.block_origin is BlockOrigin.private:
                public_block_invs.append(inv)
            else:
                private_block_invs.append(inv)

        msg = messages.msg_inv()
        if len(private_block_invs) > 0:
            msg.inv = private_block_invs
            self.connection_private.send('inv', private_block_invs)
            logging.info('{} block invs send to {}'.format(len(private_block_invs), self.connection_private.host[0]))

        if len(public_block_invs) > 0:
            msg.inv = public_block_invs
            self.connection_public.send('inv', public_block_invs)
            logging.info('{} block invs send to {}'.format(len(public_block_invs), self.connection_public.host[0]))

    def ping_message(self, connection, message):
        connection.send('pong', message)
        logging.debug('send pong to {}'.format(connection.host[0]))

    def alert_message(self, connection, message):
        logging.debug('ignoring message alert={} from {}'.format(message.alert, connection.host[0]))

    def get_headers_message(self, connection, message):
        if self.relay[connection].first_headers_ignored:
            self.relay_message(connection, message)
            return

        self.relay[connection].first_headers_ignored = True
        logging.info('ignoring first getheaders from {}'.format(connection.host[0]))

inv_typemap = {v: k for k, v in net.CInv.typemap.items()}


class Connection:

    def __init__(self, connection):
        self.connection = connection
        self.first_headers_ignored = False
