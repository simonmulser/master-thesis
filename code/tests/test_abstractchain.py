import unittest
from chain import Chain
from chain import Block
from chainutil import Fork
import chain
from mock import MagicMock
from mock import patch
from bitcoin import core
from strategy import BlockOrigin
from strategy import ActionException


class AbstractChainTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(AbstractChainTest, self).__init__(*args, **kwargs)

        self.first_block_chain_a = None
        self.second_block_chain_a = None
        self.third_a_block_chain_a = None
        self.third_b_block_chain_a = None
        self.fourth_block_chain_a = None
        self.first_block_chain_b = None
        self.second_block_chain_b = None
        self.third_a_block_chain_b = None
        self.third_b_block_chain_b = None
        self.fourth_block_chain_b = None

    def setUp(self):
        self.first_block_chain_a = Block(None, BlockOrigin.private)
        self.first_block_chain_a.height = 1
        self.first_block_chain_a.prevBlock = chain.genesis_block
        self.first_block_chain_a.cached_hash = '1a'

        self.second_block_chain_a = Block(None, BlockOrigin.private)
        self.second_block_chain_a.height = 2
        self.second_block_chain_a.prevBlock = self.first_block_chain_a
        self.second_block_chain_a.cached_hash = '2a'

        self.third_a_block_chain_a = Block(None, BlockOrigin.private)
        self.third_a_block_chain_a.height = 3
        self.third_a_block_chain_a.prevBlock = self.second_block_chain_a
        self.third_a_block_chain_a.cached_hash = '3a_1'

        self.third_b_block_chain_a = Block(None, BlockOrigin.private)
        self.third_b_block_chain_a.height = 3
        self.third_b_block_chain_a.prevBlock = self.second_block_chain_a
        self.third_b_block_chain_a.cached_hash = '3a_2'

        self.fourth_block_chain_a = Block(None, BlockOrigin.private)
        self.fourth_block_chain_a.height = 4
        self.fourth_block_chain_a.prevBlock = self.third_a_block_chain_a
        self.fourth_block_chain_a.cached_hash = '4a'

        self.first_block_chain_b = Block(None, BlockOrigin.public)
        self.first_block_chain_b.height = 1
        self.first_block_chain_b.prevBlock = chain.genesis_block
        self.first_block_chain_b.cached_hash = '1b'

        self.second_block_chain_b = Block(None, BlockOrigin.public)
        self.second_block_chain_b.height = 2
        self.second_block_chain_b.prevBlock = self.first_block_chain_b
        self.second_block_chain_b.cached_hash = '2b'

        self.third_a_block_chain_b = Block(None, BlockOrigin.public)
        self.third_a_block_chain_b.height = 3
        self.third_a_block_chain_b.prevBlock = self.second_block_chain_b
        self.third_a_block_chain_b.cached_hash = '3b_1'

        self.third_b_block_chain_b = Block(None, BlockOrigin.public)
        self.third_b_block_chain_b.height = 3
        self.third_b_block_chain_b.prevBlock = self.second_block_chain_b
        self.third_b_block_chain_b.cached_hash = '3b_2'

        self.fourth_block_chain_b = Block(None, BlockOrigin.public)
        self.fourth_block_chain_b.height = 4
        self.fourth_block_chain_b.prevBlock = self.third_a_block_chain_b
        self.fourth_block_chain_b.cached_hash = '4b'
