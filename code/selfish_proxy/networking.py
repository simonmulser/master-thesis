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

        for message in ['getaddr', 'addr', 'notfound', 'reject', 'getblocks', 'mempool']:
            client.register_handler(message, self.ignore_message)
        # also all the other messages are ignored (but not logged)

        client.register_handler('ping', self.ping_message)

        client.register_handler('inv', self.process_inv)
        client.register_handler('block', self.process_block)
        client.register_handler('headers', self.headers_message)
        client.register_handler('getheaders', self.getheaders_message)
        client.register_handler('getdata', self.getdata_message)
        # tx missing

        network.ClientBehavior(client)

        self.connection_private = client.connect((ip_private, 18444))
        for ip in ips_public:
            connection = client.connect((ip, 18444))
            self.public_connections.append(connection)

        client.run_forever()

    def process_inv(self, connection, message):
        self.lock.acquire()
        try:
            logging.debug('received inv message with {} invs from {}'
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
                    else:
                        logging.warn("we don't care about inv type={}".format(inv.type))
                except KeyError:
                    logging.warn("unknown inv type={}")

        finally:
            self.lock.release()
            logging.debug('processed inv message from {}'.format(self.repr_connection(connection)))

    def process_block(self, connection, message):
        self.lock.acquire()
        try:
            logging.debug('received block message from {}'
                          .format(self.repr_connection(connection)))

            if message.block.GetHash() in self.chain.blocks:
                block = self.chain.blocks[message.block.GetHash()]
                if block.cblock is None:
                    block.cblock = message.block
                    logging.info('set cblock in {}'.format(block.hash_repr()))
            else:
                logging.warn('received CBlock(hash={}) from {} which is not in the chain'
                             .format(core.b2lx(message.block.GetHash()), self.repr_connection(connection)))

        finally:
            self.lock.release()
            logging.debug('processed block message from {}'.format(self.repr_connection(connection)))

    def headers_message(self, connection, message):
        self.lock.acquire()
        try:
            logging.debug('received headers message with {} headers message from {}'
                          .format(len(message.headers), self.repr_connection(connection)))

            getdata_inv = []
            for header in message.headers:
                if header.GetHash() in self.chain.blocks:
                    logging.debug('already received header with hash={}'.format(core.b2lx(header.GetHash())))
                else:
                    getdata_inv.append(header.GetHash())

                    if connection == self.connection_private:
                        self.chain.process_block(header, BlockOrigin.private)
                    else:
                        self.chain.process_block(header, BlockOrigin.public)

            if len(getdata_inv) > 0:
                message = messages.msg_getdata()
                for inv in getdata_inv:
                    cInv = net.CInv()
                    cInv.type = inv_typemap['Block']
                    cInv.hash = inv
                    message.inv.append(cInv)
                connection.send('getdata', message)
                logging.info('requested getdata for {} blocks'.format(len(getdata_inv)))

        finally:
            self.lock.release()
            logging.debug('processed headers message from {}'.format(self.repr_connection(connection)))

    def getheaders_message(self, connection, message):
        self.lock.acquire()
        try:
            logging.debug('received getheaders message with {} headers from {}'
                          .format(len(message.locator.vHave), self.repr_connection(connection)))

            found_block = None
            for block_hash in message.locator.vHave:
                if block_hash in self.chain.blocks:
                    found_block = self.chain.blocks[block_hash]
                    break

            message = messages.msg_headers()
            if found_block:
                tmp = found_block.nextBlock
                while tmp and tmp.transfer_allowed:
                    message.headers.append(tmp.cblock_header)
                    tmp = tmp.nextBlock
            connection.send('headers', message)
            logging.debug('sent headers message with {} headers to {}'
                          .format(len(message.headers), self.repr_connection(connection)))

        finally:
            self.lock.release()
            logging.debug('processed getheaders message from {}'.format(self.repr_connection(connection)))

    def getdata_message(self, connection, message):
        self.lock.acquire()
        try:
            logging.debug('received getdata message with {} inv from {}'
                          .format(len(message.inv), self.repr_connection(connection)))

            for inv in message.inv:
                try:
                    if net.CInv.typemap[inv.type] == 'Block':
                        if inv.hash in self.chain.blocks:
                            if self.chain.blocks[inv.hash].cblock:
                                message = messages.msg_block()
                                message.block = self.chain.blocks[inv.hash].cblock
                                connection.send('block', message)
                                logging.info('send CBlock(hash={}) to {}'
                                             .format(core.b2lx(inv.hash), self.repr_connection(connection)))
                        else:
                            logging.info('CBlock(hash={}) not found'.format(inv.hash))
                    else:
                        logging.warn("we don't care about inv type={}".format(inv.type))
                except KeyError:
                    logging.warn("unknown inv type={}")

        finally:
            self.lock.release()
            logging.debug('processed getdata message from {}'.format(self.repr_connection(connection)))

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
                logging.debug("{} to be send to alice".format(block.hash_repr()))

        if len(private_block_invs) > 0:
            msg = messages.msg_inv()
            msg.inv = private_block_invs
            self.connection_private.send('inv', msg)
            logging.info('{} block invs send to alice'.format(len(private_block_invs)))

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

    def repr_connection(self, connection):
        if connection is self.connection_private:
            return 'private'
        else:
            return 'public(ip={})'.format(connection.host[0])

inv_typemap = {v: k for k, v in net.CInv.typemap.items()}
