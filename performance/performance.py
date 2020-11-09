import numpy as np
import pandas as pd


def create_drawdowns(pnl):
    """
    Parametri:
    pnl - Una Serie di pandas che rappresenta i rendimenti percentuali periodici.

    Restituisce:
    drawdown, duration - il massimo drawdown e la durata massima.
    """

    # Calcula la curva cumulativa dei rendimenti
    # e imposta il High Water Mark
    hwm = [0]

    # Crea le Serie del drawdown e durata
    idx = pnl.index
    drawdown = pd.Series(index = idx)
    duration = pd.Series(index = idx)

    # ciclo sul range dell'indice
    for t in range(1, len(idx)):
        hwm.append(max(hwm[t-1], pnl.ix[t]))
        drawdown.ix[t]= (hwm[t]-pnl.ix[t])
        duration.ix[t]= (0 if drawdown.ix[t] == 0 else duration.ix[t-1]+1)
    return drawdown, drawdown.max(), duration.max()