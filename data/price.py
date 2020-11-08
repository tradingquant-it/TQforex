from abc import ABCMeta, abstractmethod

from decimal import Decimal, getcontext, ROUND_HALF_DOWN

import os
import pandas as pd

from event import TickEvent


class PriceHandler(object):
    """
    PriceHandler è una classe base astratta che fornisce un'interfaccia per
    tutti i successivi gestori di dati (ereditati) (sia live che storici).

    L'obiettivo di un oggetto PriceHandler (derivato) è produrre un insieme di
    bid / ask / timestamp "tick" per ogni coppia di valute e inserirli
    una coda di eventi.

    Questo replicherà il modo in cui una strategia live funzionerebbe con i dati
    dei tick che sarebbero trasmessi in streaming tramite un broker.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def stream_to_queue(self):
        """
        Trasmette una sequenza di eventi di dati tick (timestamp, bid, ask)
        come tuple alla coda degli eventi.
        """
        raise NotImplementedError("Should implement stream_to_queue()")


class HistoricCSVPriceHandler(PriceHandler):
    """
    HistoricCSVPriceHandler è progettato per leggere un file CSV di
    dati tick per ciascuna coppia di valute richiesta e trasmetterli in streaming
    alla coda degli eventi.
    """

    def __init__(self, pairs, events_queue, csv_dir):
        """
        Inizializza il gestore dati storici richiedendo
        la posizione dei file CSV e un elenco di simboli.

        Si presume che tutti i file siano nella forma
        'pair.csv', dove " pair " è la coppia di valute. Per
        EUR/USD il nome del file è EURUSD.csv.

        Parametri:
        pairs - L'elenco delle coppie di valute da ottenere.
        events_queue - La coda degli eventi a cui inviare i tick.
        csv_dir: percorso di directory assoluto per i file CSV.
        """
        self.pairs = pairs
        self.events_queue = events_queue
        self.csv_dir = csv_dir
        self.cur_bid = None
        self.cur_ask = None

    def _open_convert_csv_files(self):
        """
        Apre i file CSV dalla directory su disco, converte i dati
        in un DataFrame di pandas con un dizionario di coppie.
        """
        pair_path = os.path.join(self.csv_dir, '%s.csv' % self.pairs[0])
        self.pair = pd.io.parsers.read_csv(
            pair_path, header=True, index_col=0, parse_dates=True,
            names=("Time", "Ask", "Bid", "AskVolume", "BidVolume")
        ).iterrows()

    def stream_to_queue(self):
        self._open_convert_csv_files()
        for index, row in self.pair:
            self.cur_bid = Decimal(str(row["Bid"])).quantize(
                Decimal("0.00001", ROUND_HALF_DOWN)
            )
            self.cur_ask = Decimal(str(row["Ask"])).quantize(
                Decimal("0.00001", ROUND_HALF_DOWN)
            )
            tev = TickEvent(self.pairs[0], index, row["Bid"], row["Ask"])
            self.events_queue.put(tev)

    def stream_next_tick(self):
        """
        Il Backtester è ora passato ad un modello a un thread singolo
        in modo da riprodurre completamente i risultati su ogni esecuzione.
        Ciò significa che il metodo stream_to_queue non può essere usato
        ed è sostituito dal metodo stream_next_tick.

        Questo metodo viene chiamato dalla funzione di backtesting, esterna
        a questa classe e inserisce un solo tick nella coda, ed inoltre
        aggiornare l'attuale bid / ask e l'inverso bid / ask.
        """
        try:
            index, row = self.all_pairs.next()
        except StopIteration:
            return
        else:
            self.prices[row["Pair"]]["bid"] = Decimal(str(row["Bid"])).quantize(
                Decimal("0.00001", ROUND_HALF_DOWN)
            )
            self.prices[row["Pair"]]["ask"] = Decimal(str(row["Ask"])).quantize(
                Decimal("0.00001", ROUND_HALF_DOWN)
            )
            self.prices[row["Pair"]]["time"] = index
            inv_pair, inv_bid, inv_ask = self.invert_prices(row)
            self.prices[inv_pair]["bid"] = inv_bid
            self.prices[inv_pair]["ask"] = inv_ask
            self.prices[inv_pair]["time"] = index
            tev = TickEvent(row["Pair"], index, row["Bid"], row["Ask"])
            self.events_queue.put(tev)