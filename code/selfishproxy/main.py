import argparse
import logging
from networking import Networking

parser = argparse.ArgumentParser(description='Running Selfish Mining Proxy.')

parser.add_argument('-v', '--verbose', help='increase output verbosity', action='store_true')

parser.add_argument('--ip-public', help='set the ip of the public node', default='240.0.0.3')

parser.add_argument('--ip-private', help='set the ip of the private node', default='240.0.0.2')

args = parser.parse_args()

logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger()

consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)

if args.verbose:
    rootLogger.setLevel(logging.DEBUG)
else:
    rootLogger.setLevel(logging.INFO)

Networking().start(args.ip_public, args.ip_private)
