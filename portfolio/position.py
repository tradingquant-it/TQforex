from decimal import Decimal, getcontext, ROUND_HALF_DOWN


class Position(object):
    def __init__(
        self, position_type, market,
        units, exposure, bid, ask
    ):
        self.position_type = position_type  # Long o short
        self.market = market
        self.units = units
        self.exposure = Decimal(str(exposure))

        # Long o short
        if self.position_type == "long":
            self.avg_price = Decimal(str(ask))
            self.cur_price = Decimal(str(bid))
        else:
            self.avg_price = Decimal(str(bid))
            self.cur_price = Decimal(str(ask))

        self.profit_base = self.calculate_profit_base(self.exposure)
        self.profit_perc = self.calculate_profit_perc(self.exposure)

    def calculate_pips(self):
        mult = Decimal("1")
        if self.position_type == "long":
            mult = Decimal("1")
        elif self.position_type == "short":
            mult = Decimal("-1")
        pips = (mult * (self.cur_price - self.avg_price)).quantize(
            Decimal("0.00001"), ROUND_HALF_DOWN
        )
        return pips

    def calculate_profit_base(self, exposure):
        pips = self.calculate_pips()
        return (pips * exposure / self.cur_price).quantize(
            Decimal("0.00001"), ROUND_HALF_DOWN
        )

    def calculate_profit_perc(self, exposure):
        return (self.profit_base / exposure * Decimal("100.00")).quantize(
            Decimal("0.00001"), ROUND_HALF_DOWN
        )

    def update_position_price(self, bid, ask, exposure):
        if self.position_type == "long":
            self.cur_price = Decimal(str(bid))
        else:
            self.cur_price = Decimal(str(ask))
        self.profit_base = self.calculate_profit_base(exposure)
        self.profit_perc = self.calculate_profit_perc(exposure)


    def add_units(self, units):
        cp = self.ticker.prices[self.currency_pair]
        if self.position_type == "long":
            add_price = cp["ask"]
        else:
            add_price = cp["bid"]
        new_total_units = self.units + units
        new_total_cost = self.avg_price * self.units + add_price * units
        self.avg_price = new_total_cost / new_total_units
        self.units = new_total_units
        self.update_position_price()

    def remove_units(self, units):
        dec_units = Decimal(str(units))
        ticker_cp = self.ticker.prices[self.currency_pair]
        ticker_qh = self.ticker.prices[self.quote_home_currency_pair]
        if self.position_type == "long":
            remove_price = ticker_cp["ask"]
            qh_close = ticker_qh["bid"]
        else:
            remove_price = ticker_cp["bid"]
            qh_close = ticker_qh["ask"]
        self.units -= dec_units
        self.update_position_price()
        # Calcolo dele PnL
        pnl = self.calculate_pips() * qh_close * dec_units
        return pnl.quantize(Decimal("0.01", ROUND_HALF_DOWN))

    def close_position(self):
        ticker_cp = self.ticker.prices[self.currency_pair]
        ticker_qh = self.ticker.prices[self.quote_home_currency_pair]
        if self.position_type == "long":
            remove_price = ticker_cp["ask"]
            qh_close = ticker_qh["bid"]
        else:
            remove_price = ticker_cp["bid"]
            qh_close = ticker_qh["ask"]
        self.update_position_price()
        # Calcolo dele PnL
        pnl = self.calculate_pips() * qh_close * self.units
        return pnl.quantize(Decimal("0.01", ROUND_HALF_DOWN))