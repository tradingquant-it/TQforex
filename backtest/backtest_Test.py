
# codice python relativo al corso "TRADING AUTOMATICO SUL FOREX"
# https://tradingquant.it/corsi/trading-automatico-sul-forex/

import copy, sys
import queue
import threading
import time
from decimal import Decimal, getcontext

from execution import SimulatedExecution
from portfolio import Portfolio
from settings import settings
from strategy import TestStrategy
from data.price import HistoricCSVPriceHandler


def trade(events, strategy, portfolio, execution, heartbeat):
    """
    Esegue un ciclo while infinito che esegue il polling
    della coda degli eventi e indirizza ogni evento al
    componente della strategia del gestore di esecuzione.
    Il ciclo si fermerà quindi per "heartbeat" secondi
    e continuerà.
    """
    while True:
        try:
            event = events.get(False)
        except queue.Empty:
            pass
        else:
            if event is not None:
                if event.type == 'TICK':
                    strategy.calculate_signals(event)
                elif event.type == 'SIGNAL':
                    portfolio.execute_signal(event)
                elif event.type == 'ORDER':
                    execution.execute_order(event)
        time.sleep(heartbeat)



def backtest(events, ticker, strategy, portfolio,
        execution, heartbeat, max_iters=200000
    ):
    """
    Esegue un ciclo while infinito che esegue il polling
    della coda degli eventi e indirizza ogni evento al
    componente della strategia del gestore di esecuzione.
    Il ciclo si fermerà quindi per "heartbeat" secondi
    e continuerà fino a quando si supera il numero massimo
    di iterazioni.
    """
    iters = 0
    while True and iters < max_iters:
        ticker.stream_next_tick()
        try:
            event = events.get(False)
        except queue.Empty:
            pass
        else:
            if event is not None:
                if event.type == 'TICK':
                    strategy.calculate_signals(event)
                elif event.type == 'SIGNAL':
                    portfolio.execute_signal(event)
                elif event.type == 'ORDER':
                    execution.execute_order(event)
        time.sleep(heartbeat)
        iters += 1
    portfolio.output_results()


if __name__ == "__main__":
    # Imposta il numero di decimali a 2
    getcontext().prec = 2

    heartbeat = 0.0  # mezzo secondo tra ogni polling
    events = queue.Queue()
    equity = settings.EQUITY

    # Carica il file CSV dei dati storici
    pairs = ["EURUSD"]
    csv_dir = settings.CSV_DATA_DIR
    if csv_dir is None:
        print("No historic data directory provided - backtest terminating.")
        sys.exit()

    # Crea la classe di streaming dei dati storici di tick
    prices = HistoricCSVPriceHandler(pairs, events, csv_dir)

    # Crea il generatore della strategia/signale, passando lo
    # strumento e la coda degli eventi
    strategy = TestStrategy(pairs[0], events)

    # Crea l'oggetto portfolio per tracciare i trade
    portfolio = Portfolio(prices, events, equity=equity)

    # Crea il gestore di esecuzione simulato
    execution = SimulatedExecution()

    # Crea due thread separati: uno per il ciclo di trading
    # e un'altro per la classe di streaming dei prezzi di mercato
    trade_thread = threading.Thread(
        target=trade, args=(
            events, strategy, portfolio, execution, heartbeat
        )
    )
    price_thread = threading.Thread(target=prices.stream_to_queue, args=[])

    # Avvia entrambi i thread
    trade_thread.start()
    price_thread.start()