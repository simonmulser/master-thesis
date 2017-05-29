import argparse
import logging
import sys
from networking import Networking
from strategy.executor import Executor
from strategy.code import Strategy
from chain import Chain


def check_positive(value):
    integer_value = int(value)
    if integer_value < 0:
        raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
    return integer_value

parser = argparse.ArgumentParser(description='Running Selfish Mining Proxy.')

parser.add_argument('-v', '--verbose', help='Increase output verbosity', action='store_true')

parser.add_argument('--ip-private', help='Set the ip of the private node', default='240.0.0.2')
parser.add_argument('--ips-public', help='Set the ips of the public nodes', nargs='+', default=[])

parser.add_argument('--lead-stubborn', help='Use lead-stubbornness in strategy', action='store_true')
parser.add_argument('--equal-fork-stubborn', help='Use equal-fork-stubbornness in strategy', action='store_true')
parser.add_argument('--trail-stubborn', help='Use N-trail-stubbornness in strategy', type=check_positive, default=0)

args = parser.parse_args()

logFormatter = logging.Formatter("%(asctime)s.%(msecs)03d000 [%(threadName)-12.12s] "
                                 "[%(levelname)-5.5s]  %(message)s", "%Y-%m-%d %H:%M:%S")
rootLogger = logging.getLogger()

fileHandler = logging.FileHandler("{0}/{1}.log".format('/tmp/', 'selfish_proxy'))
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)

if args.verbose:
    rootLogger.setLevel(logging.DEBUG)
else:
    rootLogger.setLevel(logging.INFO)

networking = Networking()
executor = Executor(networking)
strategy = Strategy(args.lead_stubborn, args.equal_fork_stubborn, args.trail_stubborn)
chain = Chain(executor, strategy)
networking.chain = chain

networking.start(args.ips_public, args.ip_private)
