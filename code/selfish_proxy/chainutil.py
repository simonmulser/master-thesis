from strategy import BlockOrigin
import chain


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
    highest_block = chain.genesis_block

    for tip in tips:
        tmp = tip
        while tmp.block_origin is not block_origin and tmp.transfer_allowed is False:
            tmp = tmp.prevBlock
        if tmp.block_origin is override_block_origin:
            if highest_block.height <= tmp.height:
                highest_block = tmp
        else:
            if highest_block.height < tmp.height:
                highest_block = tmp
    return highest_block


def get_relevant_tips(tips):
    highest_tip = max(tips, key=lambda t: t.height)
    return [tip for tip in tips if tip.height > highest_tip.height - 10]


def get_headers_after_block(tips, block):
    potential_tips = get_relevant_tips(tips)
    relevant_tips = []
    for tip in potential_tips:
        tmp = tip
        while tmp is not block and tmp.prevBlock is not None:
            tmp = tmp.prevBlock
        if tmp is block:
            relevant_tips.append(tip)

    headers = []
    if len(relevant_tips) > 0:
        highest_block = get_highest_block(relevant_tips, block.block_origin, BlockOrigin.private)

        tmp = highest_block
        while tmp is not block and tmp is not None:
            headers.append(tmp.cblock_header)
            tmp = tmp.prevBlock
    return headers


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