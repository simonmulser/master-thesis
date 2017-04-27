from bitcoinnetwork import network
import logging
from chain import Chain
from bitcoin import net
from bitcoin import messages
from actionservice import BlockOrigin

inv_type_block = 2

class Networking(object):
    def __init__(self):
        self.relay = {}
        self.connection_private = None
        self.connection_public = None
        self.chain = Chain(self)

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

        self.connection_private = client.connect(('240.0.0.2', 18444))
        self.connection_public = client.connect(('240.0.0.3', 18444))

        self.relay[self.connection_private] = self.connection_public
        self.relay[self.connection_public] = self.connection_private

        client.run_forever()

    def relay_message(self, connection, message):
        logging.debug('relaying %s message from %s:%d', message.command, *connection.host)

        self.relay[connection].send(message.command, message)

    def ping_message(self, connection, message):
        connection.send('pong', message)

    def process_inv(self, connection, message):
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
        if connection == self.connection_private:
            self.chain.process_block(message, BlockOrigin.private)
        else:
            self.chain.process_block(message, BlockOrigin.public)

    def send_inv(self, blocks):
        private_block_invs = []
        public_block_invs = []

        for block in blocks:
            inv = net.CInv()
            inv.type = inv_type_block
            inv.hash = block.hash

            if block.block_origin is BlockOrigin.private:
                public_block_invs.append(inv)
            else:
                private_block_invs.append(inv)

        msg = messages.msg_inv()
        if len(private_block_invs) > 0:
            msg.inv = private_block_invs
            self.connection_private.send('inv', private_block_invs)
        if len(public_block_invs) > 0:
            msg.inv = public_block_invs
            self.connection_public.send('inv', public_block_invs)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    Networking().start()
