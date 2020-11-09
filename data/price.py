from abc import ABCMeta, abstractmethod

from decimal import Decimal, getcontext, ROUND_HALF_DOWN

import os, os.path, re, time, datetime
import pandas as pd
import numpy as np

from settings import settings

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
    def stream_next_tick(self):
        """
        Trasmette una sequenza di eventi di dati tick (timestamp, bid, ask)
        come tuple alla coda degli eventi.
        """
        raise NotImplementedError("Should implement stream_to_queue()")

    def _set_up_prices_dict(self):
        """
        """
        prices_dict = dict(
            (k, v) for k,v in [
                (p, {"bid": None, "ask": None, "time": None}) for p in self.pairs
            ]
        )
        inv_prices_dict = dict(
            (k, v) for k,v in [
                (
                    "%s%s" % (p[3:], p[:3]),
                    {"bid": None, "ask": None, "time": None}
                ) for p in self.pairs
            ]
        )
        prices_dict.update(inv_prices_dict)
        return prices_dict


    def invert_prices(self, pair, bid, ask):
        """
        """
        getcontext().rounding = ROUND_HALF_DOWN
        inv_pair = "%s%s" % (pair[3:], pair[:3])
        inv_bid = (Decimal("1.0")/bid).quantize(
            Decimal("0.00001")
        )
        inv_ask = (Decimal("1.0")/ask).quantize(
            Decimal("0.00001")
        )
        return inv_pair, inv_bid, inv_ask


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
        self.prices = self._set_up_prices_dict()
        self.pair_frames = {}
        self.file_dates = self._list_all_file_dates()
        self.continue_backtest = True
        self.cur_date_idx = 0
        self.cur_date_pairs = self._open_convert_csv_files_for_day(
            self.file_dates[self.cur_date_idx]
        )


    def _list_all_csv_files(self):
        files = os.listdir(settings.CSV_DATA_DIR)
        pattern = re.compile("[A-Z]{6}_\d{8}.csv")
        matching_files = [f for f in files if pattern.search(f)]
        matching_files.sort()
        return matching_files

    def _list_all_file_dates(self):
        """
        Removes the pair, underscore and '.csv' from the
        dates and eliminates duplicates. Returns a list
        of date strings of the form "YYYYMMDD".
        """
        csv_files = self._list_all_csv_files()
        de_dup_csv = list(set([d[7:-4] for d in csv_files]))
        de_dup_csv.sort()
        return de_dup_csv

    def _open_convert_csv_files_for_day(self, date_str):
        """
        Apre i file CSV dalla directory su disco, converte i dati
        in un DataFrame di pandas con un dizionario di coppie.
        """
        for p in self.pairs:
            pair_path = os.path.join(self.csv_dir, '%s_%s.csv' % (p, date_str))
            self.pair_frames[p] = pd.io.parsers.read_csv(
                pair_path, header=True, index_col=0,
                parse_dates=True, dayfirst=True,
                names=("Time", "Ask", "Bid", "AskVolume", "BidVolume")
            )
            self.pair_frames[p]["Pair"] = p
        return pd.concat(self.pair_frames.values()).sort().iterrows()

    def _update_csv_for_day(self):
        try:
            dt = self.file_dates[self.cur_date_idx + 1]
        except IndexError:  # Fine del file
            return False
        else:
            self.cur_date_pairs = self._open_convert_csv_files_for_day(dt)
            self.cur_date_idx += 1
            return True


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
            index, row = next(self.cur_date_pairs)
        except StopIteration:
            # Fine dei dati per un giorno
            if self._update_csv_for_day():
                index, row = next(self.cur_date_pairs)
            else:  # Fine dei dati
                self.continue_backtest = False
                return

        getcontext().rounding = ROUND_HALF_DOWN
        pair = row["Pair"]
        bid = Decimal(str(row["Bid"])).quantize(
            Decimal("0.00001")
        )
        ask = Decimal(str(row["Ask"])).quantize(
            Decimal("0.00001")
        )

        # Create decimalised prices for traded pair
        self.prices[pair]["bid"] = bid
        self.prices[pair]["ask"] = ask
        self.prices[pair]["time"] = index

        # Create decimalised prices for inverted pair
        inv_pair, inv_bid, inv_ask = self.invert_prices(pair, bid, ask)
        self.prices[inv_pair]["bid"] = inv_bid
        self.prices[inv_pair]["ask"] = inv_ask
        self.prices[inv_pair]["time"] = index

        # Create the tick event for the queue
        tev = TickEvent(pair, index, bid, ask)
        self.events_queue.put(tev)