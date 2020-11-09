import os, os.path

import pandas as pd
import matplotlib

try:
    matplotlib.use('TkAgg')
except:
    pass
import matplotlib.pyplot as plt
import seaborn as sns

from settings import OUTPUT_RESULTS_DIR

if __name__ == "__main__":
    """
    Un semplice script per visualizzare il grafico del bilancio del portfolio, o
    "curva di equity", in funzione del tempo.

    Richiede l'impostazione di OUTPUT_RESULTS_DIR nel settings del progetto.
    """
    sns.set_palette("deep", desat=.6)
    sns.set_context(rc={"figure.figsize": (8, 4)})

    equity_file = os.path.join(OUTPUT_RESULTS_DIR, "equity.csv")
    equity = pd.io.parsers.read_csv(
        equity_file, parse_dates=True, header=0, index_col=0
    )

    # Visualizza tre grafici: curva di equity, rendimenti e drawdowns
    fig = plt.figure()
    fig.patch.set_facecolor('white')  # Imposta bianco come colore di sfondo

    # Visualizza la curva di equity
    ax1 = fig.add_subplot(311, ylabel='Portfolio value')
    equity["Equity"].plot(ax=ax1, color=sns.color_palette()[0])

    # Visualizza i rendimenti
    ax2 = fig.add_subplot(312, ylabel='Period returns')
    equity['Returns'].plot(ax=ax2, color=sns.color_palette()[1])

    # Visualizza i drawdowns
    ax3 = fig.add_subplot(313, ylabel='Drawdowns')
    equity['Drawdown'].plot(ax=ax3, color=sns.color_palette()[2])

    # Mostra i grafici
    plt.show()