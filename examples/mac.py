# codice python relativo al corso "TRADING AUTOMATICO SUL FOREX"
# https://tradingquant.it/corsi/trading-automatico-sul-forex/

from backtest import Backtest
from execution import SimulatedExecution
from portfolio import Portfolio
from settings import settings
from strategy import MovingAverageCrossStrategy
from data.price import HistoricCSVPriceHandler

if __name__ == "__main__":
    # Trading su GBP/USD e EUR/USD
    pairs = ["GBPUSD", "EURUSD"]

    # Crea i parametri della strategia per MovingAverageCrossStrategy
    strategy_params = {
        "short_window": 500,
        "long_window": 2000
    }

    # Crea ed esegue il backtest
    backtest = Backtest(
        pairs, HistoricCSVPriceHandler,
        MovingAverageCrossStrategy, strategy_params,
        Portfolio, SimulatedExecution,
        equity=settings.EQUITY
    )
    backtest.simulate_trading()