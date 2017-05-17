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
        self.public_connections = []
        self.connection_private = None
        self.chain = None
        self.lock = Lock()

    def start(self, ips_public, ip_private):
        logging.debug('starting client')

        client = network.GeventNetworkClient()

        #for message in ['notfound', 'tx', 'getblocks'
        #                'reject', 'getdata', 'mempool']:

        for message in ['getaddr', 'addr']:
            client.register_handler(message, self.ignore_message)
        # also all the other messages are ignored (but not logged)

        client.register_handler('ping', self.ping_message)

        client.register_handler('inv', self.process_inv)
        client.register_handler('block', self.process_block)
        client.register_handler('headers', self.headers_message)
        client.register_handler('getheaders', self.getheaders_message)

        network.ClientBehavior(client)

        self.connection_private = client.connect((ip_private, 18444))
        for ip in ips_public:
            connection = client.connect((ip, 18444))
            self.public_connections.append(connection)

        client.run_forever()

    def process_inv(self, connection, message):
        self.lock.acquire()
        try:
            logging.debug('received inv with {} invs from {}'
                          .format(len(message.inv), self.repr_connection(connection)))

            for inv in message.inv:
                try:
                    if net.CInv.typemap[inv.type] == "Error" or net.CInv.typemap[inv.type] == "TX":
                        pass
                    elif net.CInv.typemap[inv.type] == "Block":
                        logging.debug("received {}".format(inv))
                        if inv.hash not in self.chain.blocks:
                            get_headers = messages.msg_getheaders()
                            get_headers.locator = messages.CBlockLocator()
                            relevant_tips = chain.get_relevant_tips(self.chain.tips)
                            for tip in relevant_tips:
                                get_headers.locator.vHave = [tip.hash()]
                                connection.send('getheaders', get_headers)
                                logging.info('requested new headers {} from {}'
                                             .format(core.b2lx(tip.hash()), self.repr_connection(connection)))

                    elif net.CInv.typemap[inv.type] == "FilteredBlock":
                        logging.warn("we don't care about filtered blocks")
                    else:
                        logging.warn("unknown inv type")
                except KeyError:
                    logging.warn("unknown inv type")

        finally:
            self.lock.release()
            logging.debug('processed inv message from {}'.format(self.repr_connection(connection)))

    def process_block(self, connection, message):
        logging.info('relaying CBlock(hash={}) from {}'
                     .format(core.b2lx(message.block.GetHash()), self.repr_connection(connection)))

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
            for connection in self.public_connections:
                connection.send('inv', msg)
            logging.info('{} block invs send to public'.format(len(public_block_invs)))

    def ping_message(self, connection, message):
        connection.send('pong', message)

    def ignore_message(self, connection, message):
        logging.debug('ignoring message={} from {}'.format(message, connection.host[0]))

    def headers_message(self, connection, message):
        self.lock.acquire()
        try:
            logging.debug('received {} headers message from {}'.format(len(message.headers), self.repr_connection(connection)))

            for header in message.headers:
                if header.GetHash() in self.chain.blocks:
                    logging.debug("already received header with hash={}".format(core.b2lx(header.GetHash())))
                else:
                    if connection == self.connection_private:
                        self.chain.process_block(header, BlockOrigin.private)
                    else:
                        self.chain.process_block(header, BlockOrigin.public)
        finally:
            self.lock.release()
            logging.debug('processed headers message from {}'.format(self.repr_connection(connection)))

    def getheaders_message(self, connection, message):
        found_block = None
        for block_hash in message.locator.vHave:
            if block_hash in self.chain.blocks:
                found_block = self.chain.blocks[block_hash]
                break

        message = messages.msg_headers()
        if found_block:
            tmp = found_block.nextBlock
            while tmp and tmp.transfer_allowed:
                message.headers.append(tmp.cblock)
                tmp = tmp.nextBlock
        connection.send('headers', message)

    def repr_connection(self, connection):
        if connection is self.connection_private:
            return 'private'
        else:
            'public(ip={})'.format(connection.host[0])

inv_typemap = {v: k for k, v in net.CInv.typemap.items()}
