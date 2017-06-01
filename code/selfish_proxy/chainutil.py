from strategy import BlockOrigin
import chain
from sets import Set


def get_private_public_fork(tips):
    highest_private = get_highest_block(tips, BlockOrigin.private)
    highest_public = get_highest_block(tips, BlockOrigin.public)

    high_tip, low_tip = (highest_private, highest_public) \
        if highest_private.height > highest_public.height else (highest_public, highest_private)

    while high_tip.height > low_tip.height:
        high_tip = high_tip.prevBlock

    while high_tip is not low_tip:
        high_tip = high_tip.prevBlock
        low_tip = low_tip.prevBlock

    fork_height = high_tip.height
    return Fork(highest_private, highest_private.height - fork_height,
                highest_public, highest_public.height - fork_height)


def get_highest_block(tips, block_origin, override_block_origin=None):
    if not override_block_origin:
        override_block_origin = block_origin

    highest_block = chain.Block('start', block_origin)
    highest_block.height = -1

    for tip in get_tips_for_block_origin(tips, block_origin):
        if tip.block_origin is override_block_origin:
            if highest_block.height <= tip.height:
                highest_block = tip
        else:
            if highest_block.height < tip.height:
                highest_block = tip
    return highest_block


def get_longest_chain(tips, block_origin, until):
    block = get_highest_block(tips, block_origin, BlockOrigin.private)

    blocks = []
    while block and block.hash() not in until:
        blocks.append(block)
        block = block.prevBlock
    return blocks


def get_tips_for_block_origin(tips, block_origin):
    tips_for_block_origin = Set()
    for tip in tips:
        tmp = tip
        while tmp.block_origin is not block_origin and tmp.transfer_allowed is False:
            tmp = tmp.prevBlock
        tips_for_block_origin.add(tmp)
    return list(tips_for_block_origin)


def get_relevant_tips(tips):
    highest_tip = max(tips, key=lambda t: t.height)
    return [tip for tip in tips if tip.height > highest_tip.height - 10]


class Fork:
    def __init__(self, private_tip, private_height, public_tip, public_height):
        self.private_tip = private_tip
        self.private_height = private_height
        self.public_tip = public_tip
        self.public_height = public_height

    def __repr__(self):
        return '{}(private_height={} public_height={})' \
            .format(self.__class__.__name__, self.private_height, self.public_height)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return self.__dict__ != other.__dict__