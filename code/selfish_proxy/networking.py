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

TXS_SEND_BATCH_SIZE = 25


class Networking(object):
    def __init__(self, private_ip, sync, reconnect_time):
        self.private_ip = private_ip
        self.sync = sync
        self.reconnect_time = reconnect_time

        self.client = None
        self.chain = None
        self.txs = {}
        self.txs_with_missing_prevout = []
        self.blocks_to_send = []
        self.tx_invs_to_send_to_public = []
        self.tx_invs_to_send_to_private = []

    def start(self):
        logging.debug('starting client')

        self.client = network.GeventNetworkClient()

        for message in ['getaddr', 'addr', 'notfound', 'reject', 'getblocks', 'mempool']:
            self.client.register_handler(message, self.ignore_message)
        # all the other messages are ignored (but not logged)

        self.client.register_handler(ConnectionLostEvent.command, self.connection_lost)
        self.client.register_handler(ConnectionFailedEvent.command, self.connection_failed)
        self.client.register_handler('ping', self.ping_message)

        self.client.register_handler('inv', self.inv_message)
        self.client.register_handler('block', self.block_message)
        self.client.register_handler('headers', self.headers_message)
        self.client.register_handler('getheaders', self.getheaders_message)
        self.client.register_handler('getdata', self.getdata_message)
        self.client.register_handler('tx', self.tx_message)

        behaviour.CatchUpBehaviour(self.client, self.private_ip, self.chain)

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

            missing_inv = []
            for inv in message.inv:
                try:
                    if net.CInv.typemap[inv.type] == "Block":
                        logging.info("received block inv {} from {}".format(core.b2lx(inv.hash), self.repr_connection(connection)))
                        if inv.hash not in self.chain.blocks:
                            get_headers = messages.msg_getheaders()
                            get_headers.locator = messages.CBlockLocator()

                            if connection.host[0] == self.private_ip:
                                headers = chainutil.calc_get_headers(self.chain.tips, BlockOrigin.private)
                            else:
                                headers = chainutil.calc_get_headers(self.chain.tips, BlockOrigin.public)

                            get_headers.locator.vHave = headers
                            connection.send('getheaders', get_headers)
                            logging.info('requested new headers with {} headers and starting hash={} from {}'
                                         .format(len(headers), core.b2lx(headers[0]), self.repr_connection(connection)))
                        else:
                            logging.info('block inv {} already in local chain'.format(core.b2lx(inv.hash)))
                    elif net.CInv.typemap[inv.type] == "TX":
                        logging.debug("received {}".format(inv))
                        if inv.hash not in self.txs:
                            missing_inv.append(inv)
                    elif net.CInv.typemap[inv.type] == "Error":
                        logging.warn("received an error inv from {}".format(self.repr_connection(connection)))
                    else:
                        logging.debug("we don't care about inv type={}".format(inv.type))
                except KeyError:
                    logging.warn("unknown inv type={}")

            if len(missing_inv) > 0:
                msg = messages.msg_getdata()
                msg.inv = missing_inv
                connection.send('getdata', msg)
                logging.debug('send getdata to {}'.format(self.repr_connection(connection)))

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

                if block_hash in self.blocks_to_send:
                    self.send_inv([block])
                    self.blocks_to_send.remove(block_hash)

                for tx in message.block.vtx:
                    if tx.GetHash() in self.txs:
                        del self.txs[tx.GetHash()]
                        logging.debug('remove tx received through block and with hash={} from txs'
                                      .format(core.b2lx(tx.GetHash()), core.b2lx(block_hash)))
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
                message.inv = [hash_to_inv('Block', inv_hash) for inv_hash in getdata_inv]
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
            message.headers = [core.CBlock(block.cblock.nVersion,
                                           block.cblock.hashPrevBlock,
                                           block.cblock.hashMerkleRoot,
                                           block.cblock.nTime,
                                           block.cblock.nBits,
                                           block.cblock.nNonce) for block in blocks]
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
                                logging.warn(
                                    'Block(hash={}) requested from {} not available'
                                    .format(core.b2lx(inv.hash), self.repr_connection(connection)))
                        else:
                            logging.info('CBlock(hash={}) not found'.format(inv.hash))
                    elif net.CInv.typemap[inv.type] == 'TX':
                        tx = self.get_tx(inv.hash)
                        if tx is not None:
                            if tx.is_coinbase():
                                logging.debug('Will not relay TX(hash={}) requested from {} because it is a coinbase tx')
                            else:
                                msg = messages.msg_tx()
                                msg.tx = tx
                                connection.send('tx', msg)
                                logging.info('send TX(hash={}) to {}'.format(core.b2lx(inv.hash), self.repr_connection(connection)))
                        else:
                            logging.warn('TX(hash={}) requested from {} not available'
                                         .format(core.b2lx(inv.hash), self.repr_connection(connection)))
                    else:
                        logging.debug("we don't care about inv type={}".format(inv.type))
                except KeyError:
                    logging.warn("unknown inv type={}")

        finally:
            self.sync.lock.release()
            logging.debug('processed getdata message from {}'.format(self.repr_connection(connection)))

    def tx_message(self, connection, message):
        self.sync.lock.acquire()
        try:
            logging.debug('received tx message from {}'
                          .format(self.repr_connection(connection)))

            tx = message.tx
            tx_hash = tx.GetHash()

            if self.get_tx(tx_hash) is None:
                missing_tx = []
                for tx_in in message.tx.vin:
                    if self.get_tx(tx_in.prevout.hash) is None:
                        missing_tx.append(hash_to_inv('TX', tx_in.prevout.hash))

                if len(missing_tx) > 0:
                    msg = messages.msg_inv()
                    msg.inv = missing_tx
                    connection.send('inv', msg)
                    self.txs_with_missing_prevout.append(message.tx)
                    logging.debug('requested {} txs which are inputs of tx with hash={}'
                                  .format(len(missing_tx), core.b2lx(tx_hash)))

                else:
                    self.txs[message.tx.GetHash()] = message.tx
                    logging.debug('set tx with hash={} in transaction map'.format(core.b2lx(tx_hash)))

                    txs = [message.tx]
                    for tx_with_missing_prevout in self.txs_with_missing_prevout:
                        if all(self.get_tx(tx_in.prevout.hash) is not None for tx_in in tx_with_missing_prevout.vin):
                            txs.append(tx_with_missing_prevout)
                            self.txs_with_missing_prevout.remove(tx_with_missing_prevout)
                            logging.debug('all tx inputs of tx with hash={} are available, relaying tx with next batch'
                                          .format(core.b2lx(tx_with_missing_prevout.GetHash())))

                    for tx in txs:
                        if connection.host[0] == self.private_ip:
                            self.tx_invs_to_send_to_public.append(tx.GetHash())

                            if len(self.tx_invs_to_send_to_public) >= TXS_SEND_BATCH_SIZE:
                                msg = messages.msg_inv()
                                msg.inv = [hash_to_inv('TX', inv_hash) for inv_hash in self.tx_invs_to_send_to_public]

                                for connection in self.get_current_public_connection():
                                    connection.send('inv', msg)
                                    logging.info('send {} tx invs to connection={}'
                                                 .format(len(self.tx_invs_to_send_to_public), self.repr_connection(connection)))
                                self.tx_invs_to_send_to_public = []
                        else:
                            self.tx_invs_to_send_to_private.append(tx.GetHash())
                            if len(self.tx_invs_to_send_to_private) >= TXS_SEND_BATCH_SIZE:

                                private_connection = self.get_private_connection()

                                if private_connection is not None:
                                    msg = messages.msg_inv()
                                    msg.inv = [hash_to_inv('TX', inv_hash) for inv_hash in self.tx_invs_to_send_to_private]

                                    private_connection.send('inv', msg)
                                    logging.info('send {} tx invs to connection={}'
                                                 .format(len(self.tx_invs_to_send_to_private),
                                                         self.repr_connection(private_connection)))

                                    self.tx_invs_to_send_to_private = []
            else:
                logging.debug('already received tx with hash={}'.format(core.b2lx(tx_hash)))
        finally:
            self.sync.lock.release()
            logging.debug('processed tx message from {}'.format(self.repr_connection(connection)))

    def try_to_send_inv(self, blocks):
        relay_blocks = []
        for block in blocks:
            if block.cblock is None:
                self.blocks_to_send.append(block.hash())
            else:
                relay_blocks.append(block)

        self.send_inv(relay_blocks)

    def send_inv(self, blocks):
        private_block_invs = []
        public_block_invs = []

        for block in blocks:
            inv = hash_to_inv('Block', block.hash())
            if block.block_origin is BlockOrigin.private:
                public_block_invs.append(inv)
                logging.debug("{} to be send to public".format(block.hash_repr()))
            else:
                private_block_invs.append(inv)
                logging.debug("{} to be send to private".format(block.hash_repr()))

        if len(private_block_invs) > 0:
            private_connection = self.get_private_connection()
            if private_connection is not None:
                msg = messages.msg_inv()
                msg.inv = private_block_invs
                private_connection.send('inv', msg)
                logging.info('{} block invs send to private'.format(len(private_block_invs)))
            else:
                logging.warning('there is no connection to private (ip={})'.format(self.private_ip))

        if len(public_block_invs) > 0:
            msg = messages.msg_inv()
            msg.inv = public_block_invs

            i = 0
            for connection in self.get_current_public_connection():
                connection.send('inv', msg)
                i += 1
            logging.info('{} block invs send to {} public connections'
                         .format(len(public_block_invs), i))

    def get_tx(self, tx_hash):
        # TODO use bloom filter to know if tx is available or not

        if tx_hash in self.txs:
            logging.debug('found TX(hash={}) in mempool'.format(core.b2lx(tx_hash)))
            return self.txs[tx_hash]

        for block in self.chain.blocks.values():
            if block.cblock is not None:
                for tx in block.cblock.vtx:
                    if tx.GetHash() == tx_hash:
                        logging.debug('found TX(hash={}) in block with hash={}'
                                      .format(core.b2lx(tx_hash), core.b2lx(block.cblock.GetHash())))
                        return tx
        return None

    def ping_message(self, connection, message):
        connection.send('pong', message)

    def ignore_message(self, connection, message):
        logging.debug('ignoring message={} from {}'.format(message, connection.host[0]))

    def get_current_public_connection(self):
        for connection in self.client.connections.values():
            if connection.host[0] != self.private_ip:
                yield connection

    def get_private_connection(self):
        for connection in self.client.connections.values():
            if connection.host[0] == self.private_ip:
                return connection
        logging.warning('could not find a connection matching private_ip={}'.format(self.private_ip))
        return None

    def repr_connection(self, connection):
        if connection.host[0] == self.private_ip:
            return 'private{}'.format(connection.host)
        else:
            return 'public{}'.format(connection.host)


def hash_to_inv(inv_type, inv_hash):
    inv = net.CInv()
    inv.type = inv_typemap[inv_type]
    inv.hash = inv_hash
    return inv


inv_typemap = {v: k for k, v in net.CInv.typemap.items()}
