from bitcoinnetwork import network
import logging
from bitcoin import core
from bitcoin import net
from bitcoin import messages
from strategy import BlockOrigin
from threading import Lock
import chain


class Networking(object):
    def __init__(self):
        self.connections = {}
        self.connection_private = None
        self.connection_public = None
        self.chain = None
        self.lock = Lock()
        self.block_relay = None

    def start(self, ip_public, ip_private):
        logging.debug('starting client')

        client = network.GeventNetworkClient()

        for message in ['notfound', 'tx', 'getblocks'
                        'reject', 'getdata', 'mempool', 'getheaders']:
            client.register_handler(message, self.relay_message)

        for message in ['getaddr', 'addr']:
            client.register_handler(message, self.ignore_message)
        # also all the other messages are ignored (but not logged)

        client.register_handler('ping', self.ping_message)
        client.register_handler('getheaders', self.get_headers_message)

        client.register_handler('inv', self.process_inv)
        client.register_handler('block', self.process_block)
        client.register_handler('headers', self.headers_message)

        network.ClientBehavior(client)

        conn_private = self.connection_private = client.connect((ip_private, 18444))
        conn_public = self.connection_public = client.connect((ip_public, 18444))

        self.connections = {conn_public: Connection(conn_public, "alice-public", conn_private),
                            conn_private: Connection(conn_private, "alice-private", conn_public)}

        client.run_forever()

    def relay_message(self, connection, message):
        self.connections[connection].relay.send(message.command, message)
        logging.debug('relayed message={} from {}'.format(message.command, self.connections[connection].name))

    def process_inv(self, connection, message):
        self.lock.acquire()
        try:
            logging.debug('received inv with {} invs from {}'.format(len(message.inv), connection.host[0]))

            relay_inv = []
            for inv in message.inv:
                try:
                    if net.CInv.typemap[inv.type] == "Error" or net.CInv.typemap[inv.type] == "TX":
                        relay_inv.append(inv)
                    elif net.CInv.typemap[inv.type] == "Block":
                        logging.debug("received {}".format(inv))
                        if inv.hash in self.chain.blocks:
                            if self.chain.blocks[inv.hash].transfer_allowed:
                                relay_inv.append(inv)
                        else:
                            get_headers = messages.msg_getheaders()
                            get_headers.locator = messages.CBlockLocator()
                            relevant_tips = chain.get_relevant_tips(self.chain.tips)
                            for tip in relevant_tips:
                                get_headers.locator.vHave = [tip.hash]
                                connection.send('getheaders', get_headers)
                                logging.info('requested new headers {} from {}'
                                             .format(core.b2lx(tip.hash), self.connections[connection].name))

                    elif net.CInv.typemap[inv.type] == "FilteredBlock":
                        logging.warn("we don't care about filtered blocks")
                    else:
                        logging.warn("unknown inv type")
                except KeyError:
                    logging.warn("unknown inv type")

            if len(relay_inv) > 0:
                message.inv = relay_inv
                self.relay_message(connection, message)
        finally:
            self.lock.release()
            logging.debug('processed inv message from {}'.format(self.connections[connection].name))

    def process_block(self, connection, message):
        logging.info('relaying CBlock(hash={}) from {}'
                     .format(core.b2lx(message.block.GetHash()), self.connections[connection].name))
        self.relay_message(connection, message)

    def send_inv(self, blocks):
        private_block_invs = []
        public_block_invs = []

        for block in blocks:
            inv = net.CInv()
            inv.type = inv_typemap['Block']
            inv.hash = block.hash

            if block.block_origin is BlockOrigin.private:
                public_block_invs.append(inv)
                logging.debug("{} to be send to public".format(block.hash_repr()))
            else:
                private_block_invs.append(inv)
                logging.debug("{} to be send to alice-private".format(block.hash_repr()))

        if len(private_block_invs) > 0:
            msg = messages.msg_inv()
            msg.inv = private_block_invs
            self.connection_private.send('inv', msg)
            logging.info('{} block invs send to alice-private'.format(len(private_block_invs)))

        if len(public_block_invs) > 0:
            msg = messages.msg_inv()
            msg.inv = public_block_invs
            self.connection_public.send('inv', msg)
            self.block_relay.send_inv(msg)
            logging.info('{} block invs send to public'.format(len(public_block_invs)))

    def ping_message(self, connection, message):
        connection.send('pong', message)

    def ignore_message(self, connection, message):
        logging.debug('ignoring message={} from {}'.format(message, connection.host[0]))

    def headers_message(self, connection, message):
        self.lock.acquire()
        try:
            logging.debug('received {} headers message from {}'.format(len(message.headers), self.connections[connection].name))

            relay_headers = []
            for header in message.headers:
                if header.GetHash() in self.chain.blocks:
                    if self.chain.blocks[header.GetHash()].transfer_allowed:
                        relay_headers.append(header)
                        logging.debug("header with hash={} to be relayed".format(core.b2lx(header.GetHash())))
                else:
                    if connection == self.connection_private:
                        self.chain.process_block(header, BlockOrigin.private)
                    else:
                        self.chain.process_block(header, BlockOrigin.public)

            if len(relay_headers) > 0:
                logging.debug('there are {} block headers to be relayed'.format(len(relay_headers)))
                message.headers = relay_headers
                self.relay_message(connection, message)

        finally:
            self.lock.release()
            logging.debug('processed headers message from {}'.format(self.connections[connection].name))


inv_typemap = {v: k for k, v in net.CInv.typemap.items()}


class Connection:

    def __init__(self, connection, name, relay):
        self.connection = connection
        self.name = name
        self.relay = relay
