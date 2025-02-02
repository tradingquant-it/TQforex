import time, queue

from settings import settings

class Backtest(object):
    """
    Incaspula le impostazioni e le componenti per eseguire un backtest
    event-driven per il mercato del Forex.
    """
    def __init__(
        self, pairs, data_handler, strategy,
        strategy_params, portfolio, execution,
        equity=100000.0, heartbeat=0.0,
        max_iters=10000000000
    ):
        """
        Inizializza il backtest.
        """
        self.pairs = pairs
        self.events = queue.Queue()
        self.csv_dir = settings.CSV_DATA_DIR
        self.ticker = data_handler(self.pairs, self.events, self.csv_dir)
        self.strategy_params = strategy_params
        self.strategy = strategy(
            self.pairs, self.events, **self.strategy_params
        )
        self.equity = equity
        self.heartbeat = heartbeat
        self.max_iters = max_iters
        self.portfolio = portfolio(
            self.ticker, self.events, equity=self.equity, backtest=True
        )
        self.execution = execution()

    def _run_backtest(self):
        """
        Esegue un ciclo while infinito che esegue il polling
        della coda degli eventi e indirizza ogni evento al
        componente della strategia del gestore di esecuzione.
        Il ciclo si fermerà quindi per "heartbeat" secondi
        e continuerà fino a quando si supera il numero massimo
        di iterazioni.
        """
        print("Running Backtest...")
        iters = 0
        while iters < self.max_iters and self.ticker.continue_backtest:
            try:
                event = self.events.get(False)
            except queue.Empty:
                self.ticker.stream_next_tick()
            else:
                if event is not None:
                    if event.type == 'TICK':
                        self.strategy.calculate_signals(event)
                        self.portfolio.update_portfolio(event)
                    elif event.type == 'SIGNAL':
                        self.portfolio.execute_signal(event)
                    elif event.type == 'ORDER':
                        self.execution.execute_order(event)
            time.sleep(self.heartbeat)
            iters += 1

    def _output_performance(self):
        """
        Visualizza le performance della strategia dal backtest.
        """
        print("Calculating Performance Metrics...")
        self.portfolio.output_results()

    def simulate_trading(self):
        """
        Simula il backtest e visualizza le performance del portfolio.
        """
        self._run_backtest()
        self._output_performance()
        print("Backtest complete.")