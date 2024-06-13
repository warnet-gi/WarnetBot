import unittest

from bot.cogs.ext.tcg.utils import calculate_elo


class TestCalculateElo(unittest.TestCase):
    def test_zero_rating(self):
        rating_winner = 0.0
        rating_loser = 0.0

        self.assertEqual(20.0, calculate_elo(rating_winner, rating_loser))

    def test_non_zero_rating(self):
        rating_winner = 10.0
        rating_loser = 20.0

        self.assertEqual(20.6, calculate_elo(rating_winner, rating_loser))