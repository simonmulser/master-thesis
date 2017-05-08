import argparse
import logging
from networking import Networking

parser = argparse.ArgumentParser(description='Running Selfish Mining Proxy.')

parser.add_argument('-v', '--verbose', help='increase output verbosity', action='store_true')

parser.add_argument('--ip-public', help='set the ip of the public node', default='240.0.0.3')

parser.add_argument('--ip-private', help='set the ip of the private node', default='240.0.0.2')

args = parser.parse_args()

if args.verbose:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

Networking().start(args.ip_public, args.ip_private)
