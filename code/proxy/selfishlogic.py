import logging
from bitcoin import net
from bitcoin import messages


class SelfishLogic:

    def __init__(self):
        logging.debug("new selfish proxy")

    def process_inv_msg(self, connection, message):
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
                    logging.debug("we dont care about filtered blocks")
                else:
                    logging.debug("unknown inv type")
            except KeyError:
                logging.warn("unknown inv type")

    def process_block(self, connection, message):
        print "block"
        print message
