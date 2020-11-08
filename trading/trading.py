import queue
import threading
import time

from execution import Execution
from portfolio import Portfolio
from settings import STREAM_DOMAIN, API_DOMAIN, ACCESS_TOKEN, ACCOUNT_ID
from strategy import TestStrategy
from data import StreamingForexPrices

def trade(events, strategy, portfolio, execution):
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
                    strategy.calculate_signals(event)
                elif event.type == 'SIGNAL':
                    portfolio.execute_signal(event)
                elif event.type == 'ORDER':
                    execution.execute_order(event)
        time.sleep(heartbeat)


if __name__ == "__main__":
    heartbeat = 0.5  # Pausa di mezzo secondo
    events = queue.Queue()

    # Trading di 10000 unità di EUR/USD
    instrument = "EUR_USD"
    units = 10000

    # Creazione di una classe di streaming di prezzi da
    # OANDA, assicurandosi di fornire le credenziali
    # di autenticazione
    prices = StreamingForexPrices(
        STREAM_DOMAIN, ACCESS_TOKEN, ACCOUNT_ID,
        instrument, events
    )

    # Creazione di un gestore di esecuzione con parametri
    # di autenticazioni di OANDA
    execution = Execution(API_DOMAIN, ACCESS_TOKEN, ACCOUNT_ID)

    # Creazione del generatore di strategia/segnali, utilizzando
    # lo strumento, la quantità di unità e la coda di eventi come
    # parametri
    strategy = TestStrategy(instrument, units, events)

    # Crea un oggetto Portfolio che sarà usato per
    # confrontare le posizioni OANDA con quelle locali
    # in modo da verificare l'integrità del backtesting.
    portfolio = Portfolio(prices, events, equity=100000.0)

    # Crea due threads separati: Uno per il ciclo di trading
    # e l'altro per lo streaming dei prezzi di mercato
    trade_thread = threading.Thread(target=trade, args=(events, strategy, portfolio, execution))
    price_thread = threading.Thread(target=prices.stream_to_queue, args=[])

    # Avvio di entrambi i thread
    trade_thread.start()
    price_thread.start()

