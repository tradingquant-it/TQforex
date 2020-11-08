from copy import deepcopy
import os
import pandas as pd

from event import OrderEvent
from portfolio import Position

from settings import OUTPUT_RESULTS_DIR

class Portfolio(object):
    def __init__(
        self, ticker, events, base="EUR", leverage=20,
        equity=100000.0, risk_per_trade=0.02
    ):
        self.ticker = ticker
        self.events = events
        self.base = base
        self.leverage = leverage
        self.equity = equity
        self.balance = deepcopy(self.equity)
        self.risk_per_trade = risk_per_trade
        self.trade_units = self.calc_risk_position_size()
        self.positions = {}

    def calc_risk_position_size(self):
        return self.equity * self.risk_per_trade


    def add_new_position(self, position_type, currency_pair, units, ticker):
        ps = Position(
            self.home_currency, position_type,
            currency_pair, units, ticker
        )
        self.positions[currency_pair] = ps

    def add_position_units(self, currency_pair, units):
        if currency_pair not in self.positions:
            return False
        else:
            ps = self.positions[currency_pair]
            ps.add_units(units)
            return True

    def remove_position_units(self, currency_pair, units):
        if currency_pair not in self.positions:
            return False
        else:
            ps = self.positions[currency_pair]
            pnl = ps.remove_units(units)
            self.balance += pnl
            return True

    def close_position(self, currency_pair):
        if currency_pair not in self.positions:
            return False
        else:
            ps = self.positions[currency_pair]
            pnl = ps.close_position()
            self.balance += pnl
            del [self.positions[currency_pair]]
            return True

    def append_equity_row(self, time, balance):
        d = {"time": time, "balance": balance}
        self.equity.append(d)

    def output_results(self):
        filename = "equity.csv"
        out_file = os.path.join(OUTPUT_RESULTS_DIR, filename)
        df_equity = pd.DataFrame.from_records(self.equity, index='time')
        df_equity.to_csv(out_file)
        print
        "Simulation complete and results exported to %s" % filename

    def execute_signal(self, signal_event):
        side = signal_event.side
        market = signal_event.instrument
        units = int(self.trade_units)

        # Controlla il lato per il corretto prezzo bid/ask
        # TODO: Supporta solo i long
        add_price = self.ticker.cur_ask
        remove_price = self.ticker.cur_bid
        exposure = float(units)

        # Se non c'è una posizione, si crea una nuova
        if market not in self.positions:
            self.add_new_position(
                side, market, units, exposure,
                add_price, remove_price
            )
            order = OrderEvent(market, units, "market", "buy")
            self.events.put(order)
        # Se la posizione esiste, si aggiunge o rimuove unità
        else:
            ps = self.positions[market]
            # controlla se il lato è coerente con il lato della posizione
            if side == ps.side:
                # aggiunge unità alla posizione
                self.add_position_units(market, units, exposure,
                                        add_price, remove_price
                                        )
            else:
                # Controlla se ci sono unità nella posizione
                if units == ps.units:
                    # Chiude la posizione
                    self.close_position(market, remove_price)
                    order = OrderEvent(market, units, "market", "sell")
                    self.events.put(order)
                elif units < ps.units:
                    # Rimuove unità dalla posizione
                    self.remove_position_units(
                        market, units, remove_price
                    )
                else:  # units > ps.units
                    # Chiude la posizione e crea una nuova posizione
                    # nel lato opposto con le unità rimanenti
                    new_units = units - ps.units
                    self.close_position(market, remove_price)

                    if side == "buy":
                        new_side = "sell"
                    else:
                        new_side = "sell"
                    new_exposure = float(units)
                    self.add_new_position(
                        new_side, market, new_units,
                        new_exposure, add_price, remove_price
                    )
        print
        "Balance: %0.2f" % self.balance

