
import pool

class BalanceDelta():

    def __init__(self, pool, asset1_delta, asset2_delta, lp_delta):
        """Constructor method for :class:`BalanceDelta`
        :param pool: a :class:`Pool` object for querying pool data
        :type pool: :class:`Pool`
        :param asset1_delta: change in the asset 1 balance of the pool
        :type asset1_delta: int
        :param asset2_delta: change in the asset 2 balance of the pool
        :type asset2_delta: int
        :param lp_delta: change in the lp balance of the pool
        :type lp_delta: int
        """

        self.asset1_delta = asset1_delta
        self.asset2_delta = asset2_delta
        self.lp_delta = lp_delta

        if (lp_delta == 0):
            self.price_delta = 0
        elif (pool.lp_circulation == 0):
            self.price_delta = 0
        else:
            starting_price_ratio = pool.asset1_balance / pool.asset2_balance
            final_price_ratio = (pool.asset1_balance + asset1_delta) / (pool.asset2_balance + asset2_delta)
            self.price_delta = abs((starting_price_ratio / final_price_ratio) - 1)