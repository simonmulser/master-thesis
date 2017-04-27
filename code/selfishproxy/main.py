import argparse
import logging
from networking import Networking

parser = argparse.ArgumentParser(description='Running Selfish Mining Proxy.')

parser.add_argument('-v', '--verbose', help='increase output verbosity', action='store_true')

args = parser.parse_args()
if args.verbose:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

Networking().start()
