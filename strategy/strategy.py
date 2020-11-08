import random

from event import OrderEvent


class TestRandomStrategy(object):
    def __init__(self, instrument, units, events):
        self.instrument = instrument
        self.units = units
        self.events = events
        self.ticks = 0

    def calculate_signals(self, event):
        if event.type == 'TICK':
            self.ticks += 1
            if self.ticks % 5 == 0:
                side = random.choice(["buy", "sell"])
                order = OrderEvent(
                    self.instrument, self.units, "market", side
                )
                self.events.put(order)


from event import SignalEvent

class TestStrategy(object):
    def __init__(self, instrument, events):
        self.instrument = instrument
        self.events = events
        self.ticks = 0
        self.invested = False

    def calculate_signals(self, event):
        if event.type == 'TICK':
            self.ticks += 1
            if self.ticks % 5 == 0:
                if self.invested == False:
                    signal = SignalEvent(self.instrument, "market", "buy")
                    self.events.put(signal)
                    self.invested = True
                else:
                    signal = SignalEvent(self.instrument, "market", "sell")
                    self.events.put(signal)
                    self.invested = False


class MovingAverageCrossStrategy(object):
    """
    Una strategia base di Moving Average Crossover che genera
    due medie mobili semplici (SMA), con finestre predefinite
    di 500 tick per la SMA  breve e 2.000 tick per la SMA
    lunga.

    La strategia è "solo long" nel senso che aprirà solo una
    posizione long una volta che la SMA breve supera la SMA
    lunga. Chiuderà la posizione (prendendo un corrispondente
    ordine di vendita) quando la SMA lunga incrocia nuovamente
    la SMA breve.

    La strategia utilizza un calcolo SMA a rotazione per
    aumentare l'efficienza eliminando la necessità di chiamare due
    calcoli della media mobile completa su ogni tick.
    """

    def __init__(
            self, pairs, events,
            short_window=500, long_window=2000
    ):
        self.pairs = pairs
        self.events = events
        self.ticks = 0
        self.invested = False

        self.short_window = short_window
        self.long_window = long_window
        self.short_sma = None
        self.long_sma = None

    def calc_rolling_sma(self, sma_m_1, window, price):
        return ((sma_m_1 * (window - 1)) + price) / window

    def calculate_signals(self, event):
        if event.type == 'TICK':
            price = event.bid
            if self.ticks == 0:
                self.short_sma = price
                self.long_sma = price
            else:
                self.short_sma = self.calc_rolling_sma(
                    self.short_sma, self.short_window, price
                )
                self.long_sma = self.calc_rolling_sma(
                    self.long_sma, self.long_window, price
                )
            # Si avvia la strategia solamente dopo aver creato una accurata finestra di breve periodo
            if self.ticks > self.short_window:
                if self.short_sma > self.long_sma and not self.invested:
                    signal = SignalEvent(self.pairs[0], "market", "buy", event.time)
                    self.events.put(signal)
                    self.invested = True
                if self.short_sma < self.long_sma and self.invested:
                    signal = SignalEvent(self.pairs[0], "market", "sell", event.time)
                    self.events.put(signal)
                    self.invested = False
            self.ticks += 1