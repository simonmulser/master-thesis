from enum import Enum
import logging


class Strategy:

    def __init__(self, strategy):
        self.fork_state = ForkState.irrelevant
        self.strategy = strategy

    def find_action(self, length_private, length_public, last_block_origin):
        if length_private is 0 and length_public is 0:
            raise ActionException('both lengths can\'t be zero')

        if self.fork_state is ForkState.active:
            if last_block_origin is BlockOrigin.private and length_private <= length_public:
                self.fork_state = ForkState.irrelevant
                raise ActionException('fork_state=active, block_origin=private and '
                                             'length_private <= length_public')
            elif last_block_origin is BlockOrigin.public and length_private < length_public:
                self.fork_state = ForkState.irrelevant
                raise ActionException('fork_state=active, block_origin=public and '
                                             'length_private < length_public')

        logging.debug('find action old fork_state={}'.format(self.fork_state))
        if last_block_origin is BlockOrigin.public and length_public <= length_private:
            self.fork_state = ForkState.relevant
        elif last_block_origin is BlockOrigin.private and self.fork_state is ForkState.active:
            self.fork_state = ForkState.active
        else:
            self.fork_state = ForkState.irrelevant
        logging.debug('find action new fork_state={}'.format(self.fork_state))

        action = Action(self.strategy[self.fork_state.value][length_private][length_public])
        logging.info('found action={} with length_private={} length_public={} last_block_origin={} fork_state={} '
                      .format(action, length_private, length_public, last_block_origin, self.fork_state))

        if action is Action.match:
            self.fork_state = ForkState.active

        return action


class Action(Enum):
    adopt = 'a'
    override = 'o'
    match = 'm'
    wait = 'w'


class ForkState(Enum):
    irrelevant = 0
    relevant = 1
    active = 2


class BlockOrigin(Enum):
    private = 0
    public = 1


class ActionException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)
