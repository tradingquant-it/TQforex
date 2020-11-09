import copy
from decimal import Decimal, getcontext
import logging
import logging.config

import queue
import threading
import time

from execution import OANDAExecutionHandler
from portfolio import Portfolio
from settings import STREAM_DOMAIN, API_DOMAIN, ACCESS_TOKEN, ACCOUNT_ID
from strategy import TestStrategy
from data import StreamingForexPrices
from settings import settings

def trade(events, strategy, portfolio, execution, heartbeat):
    """
    Esegue un ciclo while infinito che effettua il polling
    della coda degli eventi e indirizza ogni evento al
    componente strategia del gestore di esecuzione.
    Il ciclo si fermerà per "heartbeat" di alcuni secondi
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
                    logger.info("Received new tick event: %s", event)
                    strategy.calculate_signals(event)
                    portfolio.update_portfolio(event)
                elif event.type == 'SIGNAL':
                    logger.info("Received new signal event: %s", event)
                    portfolio.execute_signal(event)
                elif event.type == 'ORDER':
                    logger.info("Received new order event: %s", event)
                    execution.execute_order(event)
        time.sleep(heartbeat)


if __name__ == "__main__":
    logging.config.fileConfig('../logging.conf')
    logger = logging.getLogger('qsforex.trading.trading')

    heartbeat = 0.5  # Pausa di mezzo secondo
    events = queue.Queue()
    equity = settings.EQUITY

    # coppie di valute da negoziare
    pairs = ["EURUSD", "GBPUSD"]

    # Creazione di una classe di streaming di prezzi da
    # OANDA, assicurandosi di fornire le credenziali
    # di autenticazione
    prices = StreamingForexPrices(
        STREAM_DOMAIN, ACCESS_TOKEN, ACCOUNT_ID,
        pairs, events
    )

    # Creazione del generatore di strategia/segnali, utilizzando
    # lo strumento, la quantità di unità e la coda di eventi come
    # parametri
    strategy = TestStrategy(pairs, events)

    # Crea un oggetto Portfolio che sarà usato per
    # confrontare le posizioni OANDA con quelle locali
    # in modo da verificare l'integrità del backtesting.
    portfolio = Portfolio(prices, events, equity=equity, backtest=False)

    # Creazione di un gestore di esecuzione con parametri
    # di autenticazioni di OANDA
    execution = OANDAExecutionHandler(API_DOMAIN, ACCESS_TOKEN, ACCOUNT_ID)

    # Crea due threads separati: Uno per il ciclo di trading
    # e l'altro per lo streaming dei prezzi di mercato
    trade_thread = threading.Thread(target=trade, args=(events, strategy, portfolio, execution, heartbeat))
    price_thread = threading.Thread(target=prices.stream_to_queue, args=[])

    # Avvio di entrambi i thread
    logger.info("Starting trading thread")
    trade_thread.start()
    logger.info("Starting price streaming thread")
    price_thread.start()

