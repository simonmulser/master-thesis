from bitcoinnetwork import network
from bitcoinnetwork.network import ConnectionLostEvent
from bitcoinnetwork.network import ConnectionFailedEvent
import logging
from bitcoin import core
from bitcoin import net
from bitcoin import messages
from strategy import BlockOrigin
import chainutil
import behaviour
import gevent


class Networking(object):
    def __init__(self, sync, reconnect_time):
        self.sync = sync
        self.reconnect_time = reconnect_time

        self.client = None
        self.chain = None
        self.deferred_requests = {}
        self.transactions = {}
        self.private_ip = None

    def start(self, private_ip):
        logging.debug('starting client')
        self.private_ip = private_ip

        self.client = network.GeventNetworkClient()

        for message in ['getaddr', 'addr', 'notfound', 'reject', 'getblocks', 'mempool']:
            self.client.register_handler(message, self.ignore_message)
        # also all the other messages are ignored (but not logged)

        self.client.register_handler(ConnectionLostEvent.command, self.connection_lost)
        self.client.register_handler(ConnectionFailedEvent.command, self.connection_failed)
        self.client.register_handler('ping', self.ping_message)

        self.client.register_handler('inv', self.inv_message)
        self.client.register_handler('block', self.block_message)
        self.client.register_handler('headers', self.headers_message)
        self.client.register_handler('getheaders', self.getheaders_message)
        self.client.register_handler('getdata', self.getdata_message)

        behaviour.ClientBehaviourWithCatchUp(self.client, private_ip)

        self.client.listen(port=18444)

        self.client.run_forever()

    def connection_failed(self, connection, message=None):
        logging.warn('Connecting to host={} failed'.format(connection.host, self.reconnect_time))

    def connection_lost(self, connection, message=None):
        logging.warn('Connecting to host={} lost'.format(connection.host, self.reconnect_time))

    def inv_message(self, connection, message):
        self.sync.lock.acquire()
        try:
            logging.debug('received inv message with {} invs from {}'
                          .format(len(message.inv), self.repr_connection(connection)))
            for inv in message.inv:
                try:
                    if net.CInv.typemap[inv.type] == "Block":
                        logging.info("received block inv {} from {}".format(core.b2lx(inv.hash), self.repr_connection(connection)))
                        if inv.hash not in self.chain.blocks:
                            get_headers = messages.msg_getheaders()
                            get_headers.locator = messages.CBlockLocator()

                            if connection.host[0] == self.private_ip:
                                relevant_tips = chainutil.get_tips_for_block_origin(self.chain.tips, BlockOrigin.private)
                            else:
                                relevant_tips = chainutil.get_tips_for_block_origin(self.chain.tips, BlockOrigin.public)

                            relevant_tips = chainutil.get_relevant_tips(relevant_tips)

                            for tip in relevant_tips:
                                get_headers.locator.vHave = [tip.hash()]
                                connection.send('getheaders', get_headers)
                                logging.info('requested new headers {} from {}'
                                             .format(core.b2lx(tip.hash()), self.repr_connection(connection)))
                        else:
                            logging.info('block inv {} already in local chain'.format(core.b2lx(inv.hash)))
                    elif net.CInv.typemap[inv.type] == "Error":
                        logging.warn("received an error inv from {}".format(self.repr_connection(connection)))
                    else:
                        logging.debug("we don't care about inv type={}".format(inv.type))
                except KeyError:
                    logging.warn("unknown inv type={}")

        finally:
            self.sync.lock.release()
            logging.debug('processed inv message from {}'.format(self.repr_connection(connection)))

    def block_message(self, connection, message):
        self.sync.lock.acquire()
        try:
            logging.debug('received block message from {}'
                          .format(self.repr_connection(connection)))

            block_hash = message.block.GetHash()
            if block_hash in self.chain.blocks:
                block = self.chain.blocks[block_hash]
                if block.cblock is None:
                    block.cblock = message.block
                    logging.info('set cblock in {}'.format(block.hash_repr()))

                if block_hash in self.deferred_requests:
                    for saved_connection in self.deferred_requests[block_hash]:
                        saved_connection.send('block', message)
                        logging.info('full-filled deferred block request for CBlock(hash={}) to {}'
                                     .format(core.b2lx(block_hash), self.repr_connection(saved_connection)))

                    self.deferred_requests[block_hash] = []
            else:
                logging.warn('received CBlock(hash={}) from {} which is not in the chain'
                             .format(core.b2lx(block_hash), self.repr_connection(connection)))

        finally:
            self.sync.lock.release()
            logging.debug('processed block message from {}'.format(self.repr_connection(connection)))

    def headers_message(self, connection, message):
        self.sync.lock.acquire()
        try:
            logging.debug('received headers message with {} headers message from {}'
                          .format(len(message.headers), self.repr_connection(connection)))

            getdata_inv = []
            for header in message.headers:
                if header.GetHash() in self.chain.blocks:
                    logging.debug('already received header with hash={}'.format(core.b2lx(header.GetHash())))
                else:
                    logging.debug('received header with hash={} from {}'
                                  .format(core.b2lx(header.GetHash()), self.repr_connection(connection)))
                    getdata_inv.append(header.GetHash())

                    if connection.host[0] == self.private_ip:
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
            self.sync.lock.release()
            logging.debug('processed headers message from {}'.format(self.repr_connection(connection)))

    def getheaders_message(self, connection, message):
        self.sync.lock.acquire()
        try:
            logging.debug('received getheaders message with {} headers from {}'
                          .format(len(message.locator.vHave), self.repr_connection(connection)))

            if connection.host[0] == self.private_ip:
                blocks = chainutil.get_longest_chain(self.chain.tips, BlockOrigin.private, message.locator.vHave)
            else:
                blocks = chainutil.get_longest_chain(self.chain.tips, BlockOrigin.public, message.locator.vHave)

            message = messages.msg_headers()
            message.headers = [block.cblock_header for block in blocks][::-1]
            connection.send('headers', message)
            logging.debug('sent headers message with {} headers to {}'
                          .format(len(message.headers), self.repr_connection(connection)))

        finally:
            self.sync.lock.release()
            logging.debug('processed getheaders message from {}'.format(self.repr_connection(connection)))

    def getdata_message(self, connection, message):
        self.sync.lock.acquire()
        try:
            logging.debug('received getdata message with {} inv from {}'
                          .format(len(message.inv), self.repr_connection(connection)))

            for inv in message.inv:
                try:
                    if net.CInv.typemap[inv.type] == 'Block':
                        if inv.hash in self.chain.blocks:
                            if self.chain.blocks[inv.hash].cblock:
                                msg = messages.msg_block()
                                msg.block = self.chain.blocks[inv.hash].cblock
                                connection.send('block', msg)
                                logging.info('send CBlock(hash={}) to {}'
                                             .format(core.b2lx(inv.hash), self.repr_connection(connection)))
                            else:
                                if inv.hash in self.deferred_requests:
                                    self.deferred_requests[inv.hash].append(connection)
                                else:
                                    self.deferred_requests[inv.hash] = [connection]
                                logging.info('CBlock(hash={}) not available, added to deferred_requests'
                                             .format(core.b2lx(inv.hash), self.repr_connection(connection)))
                        else:
                            logging.info('CBlock(hash={}) not found'.format(inv.hash))
                    else:
                        logging.debug("we don't care about inv type={}".format(inv.type))
                except KeyError:
                    logging.warn("unknown inv type={}")

        finally:
            self.sync.lock.release()
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
                logging.debug("{} to be send to private".format(block.hash_repr()))

        public_connections = []
        private_connection = None
        for connection in self.client.connections.values():
            if connection.host[0] == self.private_ip:
                if private_connection is None:
                    private_connection = connection
                else:
                    logging.error('there are more than one private connections to ip={}'.format(self.private_ip))
            else:
                public_connections.append(connection)

        if len(private_block_invs) > 0:
            msg = messages.msg_inv()
            msg.inv = private_block_invs
            if private_connection is not None:
                private_connection.send('inv', msg)
                logging.info('{} block invs send to private'.format(len(private_block_invs)))
            else:
                logging.error('there is no connection to private (ip={})'.format(self.private_ip))

        if len(public_block_invs) > 0:
            msg = messages.msg_inv()
            msg.inv = public_block_invs
            for connection in public_connections:
                connection.send('inv', msg)
            logging.info('{} block invs send to {} public connections'
                         .format(len(public_block_invs), len(public_connections)))

    def ping_message(self, connection, message):
        connection.send('pong', message)

    def ignore_message(self, connection, message):
        logging.debug('ignoring message={} from {}'.format(message, connection.host[0]))

    def repr_connection(self, connection):
        if connection.host[0] == self.private_ip:
            return 'private{}'.format(connection.host)
        else:
            return 'public{}'.format(connection.host)


inv_typemap = {v: k for k, v in net.CInv.typemap.items()}
