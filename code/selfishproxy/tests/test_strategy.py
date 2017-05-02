import unittest
from strategy import Strategy
from strategy import ActionException
from strategy import Action
from strategy import BlockOrigin
from strategy import ForkState


class StrategyTest(unittest.TestCase):

    def setUp(self):
        self.strategy = [
            [  # irrelevant
                ['*', '*', '*'],
                ['*', '*', '*'],
                ['*', '*', '*']
            ],
            [  # relevant
                ['*', '*', '*'],
                ['*', '*', '*'],
                ['*', '*', '*']
            ],
            [  # match
                ['*', '*', '*'],
                ['*', '*', '*'],
                ['*', '*', '*']
            ]
        ]

    def test_find_action_both_height_zero(self):
        action_service = Strategy([])

        with self.assertRaisesRegexp(ActionException, "lengths can\'t be zero"):
            action_service.find_action(0, 0, None)

        self.assertNotEqual(action_service.fork_state, ForkState.active)

    def test_find_action_state_unreachable(self):
        action_service = Strategy(self.strategy)
        action_service.fork_state = ForkState.irrelevant

        action = action_service.find_action(1, 1, BlockOrigin.public)
        self.assertEqual(action, Action.adopt)
        self.assertEqual(action_service.fork_state, ForkState.irrelevant)

    def test_find_action_block_origin_public_same_height(self):
        self.strategy[ForkState.relevant.value][2][2] = 'w'
        action_service = Strategy(self.strategy)
        action_service.fork_state = ForkState.irrelevant

        action = action_service.find_action(2, 2, BlockOrigin.public)

        self.assertEqual(action, Action.wait)
        self.assertNotEqual(action_service.fork_state, ForkState.active)

    def test_find_action_block_origin_public_lead_private(self):
        self.strategy[ForkState.relevant.value][1][0] = 'w'
        action_service = Strategy(self.strategy)
        action_service.fork_state = ForkState.irrelevant

        action = action_service.find_action(1, 0, BlockOrigin.public)

        self.assertEqual(action, Action.wait)
        self.assertNotEqual(action_service.fork_state, ForkState.active)

    def test_find_action_block_origin_public_lead_public(self):
        self.strategy[ForkState.irrelevant.value][0][1] = 'w'
        action_service = Strategy(self.strategy)
        action_service.fork_state = ForkState.irrelevant

        action = action_service.find_action(0, 1, BlockOrigin.public)

        self.assertEqual(action, Action.wait)
        self.assertNotEqual(action_service.fork_state, ForkState.active)

    def test_find_action_block_origin_public_same_height_fork_state_active(self):
        self.strategy[ForkState.relevant.value][2][2] = 'w'
        action_service = Strategy(self.strategy)
        action_service.fork_state = ForkState.active

        action = action_service.find_action(2, 2, BlockOrigin.public)

        self.assertEqual(action, Action.wait)
        self.assertNotEqual(action_service.fork_state, ForkState.active)

    def test_find_action_block_origin_public_lead_private_fork_state_active(self):
        self.strategy[ForkState.relevant.value][1][0] = 'w'
        action_service = Strategy(self.strategy)
        action_service.fork_state = ForkState.active

        action = action_service.find_action(1, 0, BlockOrigin.public)

        self.assertEqual(action, Action.wait)
        self.assertNotEqual(action_service.fork_state, ForkState.active)

    def test_find_action_block_origin_public_lead_public_fork_state_active(self):
        action_service = Strategy([[[]]])
        action_service.fork_state = ForkState.active

        with self.assertRaisesRegexp(ActionException, ".*active.*public.*length_private < length_public"):
            action_service.find_action(0, 1, BlockOrigin.public)

        self.assertNotEqual(action_service.fork_state, ForkState.active)

    def test_find_action_block_origin_private_same_height(self):
        self.strategy[ForkState.irrelevant.value][2][2] = 'w'
        action_service = Strategy(self.strategy)
        action_service.fork_state = ForkState.irrelevant

        action = action_service.find_action(2, 2, BlockOrigin.private)

        self.assertEqual(action, Action.wait)
        self.assertNotEqual(action_service.fork_state, ForkState.active)

    def test_find_action_block_origin_private_lead_private(self):
        self.strategy[ForkState.irrelevant.value][1][0] = 'w'
        action_service = Strategy(self.strategy)
        action_service.fork_state = ForkState.irrelevant

        action = action_service.find_action(1, 0, BlockOrigin.private)

        self.assertEqual(action, Action.wait)
        self.assertNotEqual(action_service.fork_state, ForkState.active)

    def test_find_action_block_origin_private_lead_public(self):
        self.strategy[ForkState.irrelevant.value][0][1] = 'w'
        action_service = Strategy(self.strategy)
        action_service.fork_state = ForkState.irrelevant

        action = action_service.find_action(0, 1, BlockOrigin.private)

        self.assertEqual(action, Action.wait)
        self.assertNotEqual(action_service.fork_state, ForkState.active)

    def test_find_action_block_origin_private_same_height_fork_state_active(self):
        action_service = Strategy([[[]]])
        action_service.fork_state = ForkState.active

        with self.assertRaisesRegexp(ActionException, ".*active.*private.*length_private <= length_public"):
            action_service.find_action(2, 2, BlockOrigin.private)

        self.assertNotEqual(action_service.fork_state, ForkState.active)

    def test_find_action_block_origin_private_lead_private_fork_state_active(self):
        self.strategy[ForkState.active.value][1][0] = 'w'
        action_service = Strategy(self.strategy)
        action_service.fork_state = ForkState.active

        action = action_service.find_action(1, 0, BlockOrigin.private)

        self.assertEqual(action, Action.wait)
        self.assertEqual(action_service.fork_state, ForkState.active)

    def test_find_action_block_origin_private_lead_public_fork_state_active(self):
        action_service = Strategy([[[]]])
        action_service.fork_state = ForkState.active

        with self.assertRaisesRegexp(ActionException, ".*active.*private.*length_private <= length_public"):
            action_service.find_action(0, 1, BlockOrigin.private)

        self.assertNotEqual(action_service.fork_state, ForkState.active)
