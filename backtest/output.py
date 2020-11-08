import os, os.path

import pandas as pd
import matplotlib.pyplot as plt

from settings import OUTPUT_RESULTS_DIR


if __name__ == "__main__":
    """
    Un semplice script per visualizzare il grafico del bilancio del portfolio, o
    "curva di equity", in funzione del tempo.

    Richiede l'impostazione di OUTPUT_RESULTS_DIR nel settings del progetto.
    """
    equity_file = os.path.join(OUTPUT_RESULTS_DIR, "equity.csv")
    equity = pd.io.parsers.read_csv(
        equity_file, header=True,
        names=["time", "balance"],
        parse_dates=True, index_col=0
    )
    equity["balance"].plot()
    plt.show()