
# codice python relativo al corso "TRADING AUTOMATICO SUL FOREX"
# https://tradingquant.it/corsi/trading-automatico-sul-forex/

from copy import deepcopy
from decimal import Decimal, getcontext, ROUND_HALF_DOWN
import logging
import os

import pandas as pd

from event import OrderEvent
from portfolio import Position
from performance import create_drawdowns

from settings import OUTPUT_RESULTS_DIR

class Portfolio(object):
    def __init__(
            self, ticker, events, home_currency="GBP",
            leverage=20, equity=Decimal("100000.00"),
            risk_per_trade=Decimal("0.02"), backtest=True
    ):
        self.ticker = ticker
        self.events = events
        self.home_currency = home_currency
        self.leverage = leverage
        self.equity = equity
        self.balance = deepcopy(self.equity)
        self.risk_per_trade = risk_per_trade
        self.backtest = backtest
        self.trade_units = self.calc_risk_position_size()
        self.positions = {}
        if self.backtest:
            self.backtest_file = self.create_equity_file()
        self.logger = logging.getLogger(__name__)

    def calc_risk_position_size(self):
        return self.equity * self.risk_per_trade

    def add_new_position(
            self, position_type, currency_pair, units, ticker
    ):
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

    def create_equity_file(self):
        filename = "backtest.csv"
        out_file = open(os.path.join(OUTPUT_RESULTS_DIR, filename), "w")
        header = "Timestamp,Balance"
        for pair in self.ticker.pairs:
            header += ",%s" % pair
        header += "\n"
        out_file.write(header)
        if self.backtest:
            print(header[:-2])
        return out_file

    def output_results(self):
        # Chiusura del file csv del backtest.csv cosiì da poter
        # essere caricato con Pandas senza errori
        self.backtest_file.close()

        in_filename = "backtest.csv"
        out_filename = "equity.csv"
        in_file = os.path.join(OUTPUT_RESULTS_DIR, in_filename)
        out_file = os.path.join(OUTPUT_RESULTS_DIR, out_filename)

        # Crea il dataframe della curva di equity
        df = pd.read_csv(in_file, index_col=0)
        df.dropna(inplace=True)
        df["Total"] = df.sum(axis=1)
        df["Returns"] = df["Total"].pct_change()
        df["Equity"] = (1.0 + df["Returns"]).cumprod()

        # Crea le statistiche di drawdown
        drawdown, max_dd, dd_duration = create_drawdowns(df["Equity"])
        df["Drawdown"] = drawdown
        df.to_csv(out_file, index=True)

        print("Simulation complete and results exported to %s" % out_filename)


    def update_portfolio(self, tick_event):
        """
        Aggiorna tutte le posizione assicurandosi di aggiornarne
        il profit and loss (PnL) non realizzato.
        """
        currency_pair = tick_event.instrument
        if currency_pair in self.positions:
            ps = self.positions[currency_pair]
            ps.update_position_price()
        if self.backtest:
            out_line = "%s,%s" % (tick_event.time, self.balance)
            for pair in self.ticker.pairs:
                if pair in self.positions:
                    out_line += ",%s" % self.positions[pair].profit_base
                else:
                    out_line += ",0.00"
            out_line += "\n"
            print(out_line[:-2])
            self.backtest_file.write(out_line)


    def execute_signal(self, signal_event):
        # Controlla se il ticker dei prezzi contiene tutte
        # le coppie di valute per eseguire l'ordine
        execute = True
        tp = self.ticker.prices
        for pair in tp:
            if tp[pair]["ask"] is None or tp[pair]["bid"] is None:
                execute = False

        # Tutti i dati dei prezzi sono dispponibile
        # è possibile eseguire l'ordine
        if execute:

            side = signal_event.side
            currency_pair = signal_event.instrument
            units = int(self.trade_units)
            time = signal_event.time

            # Se non c'è una posizione, si crea una nuova
            if currency_pair not in self.positions:
                if side == "buy":
                    position_type = "long"
                else:
                    position_type = "short"
                self.add_new_position(
                    position_type, currency_pair,
                    units, self.ticker
                )

            # Se la posizione esiste, si aggiunge o rimuove unità
            else:
                ps = self.positions[currency_pair]

                # controlla se il lato è coerente con il lato della posizione
                if side == "buy" and ps.position_type == "long":
                    # aggiunge unità alla posizione
                    self.add_position_units(currency_pair, units)

                elif side == "sell" and ps.position_type == "long":
                    # Controlla se ci sono unità nella posizione
                    if units == ps.units:
                        # Chiude la posizione
                        self.close_position(currency_pair)
                    elif units < ps.units:
                        # TODO: Rimuove unità dalla posizione
                        return
                    else:  # units > ps.units
                        # TODO: Chiude la posizione e crea una nuova posizione
                        # nel lato opposto con le unità rimanenti
                        return

                elif side == "buy" and ps.position_type == "short":
                    if units == ps.units:
                        self.close_position(currency_pair)
                    # TODO: aggiungere/rimuovere posizioni
                    elif units < ps.units:
                        return
                    elif units > ps.units:
                        return

                elif side == "sell" and ps.position_type == "short":
                    self.add_position_units(currency_pair, units)

            order = OrderEvent(currency_pair, units, "market", side)
            self.events.put(order)

            self.logger.info("Portfolio Balance: %s" % self.balance)
        else:
            self.logger.info("Unable to execute order as price data was insufficient.")


