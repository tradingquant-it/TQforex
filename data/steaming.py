
# codice python relativo al corso "TRADING AUTOMATICO SUL FOREX"
# https://tradingquant.it/corsi/trading-automatico-sul-forex/

import requests, logging
import json
from decimal import Decimal, getcontext, ROUND_HALF_DOWN

from event import TickEvent
from data import PriceHandler

class StreamingForexPrices(object):
    def __init__(
        self, domain, access_token,
        account_id, pairs, events_queue
    ):
        self.domain = domain
        self.access_token = access_token
        self.account_id = account_id
        self.events_queue = events_queue
        self.pairs = pairs
        self.prices = self._set_up_prices_dict()
        self.logger = logging.getLogger(__name__)

    def invert_prices(self, pair, bid, ask):
        """
        Inverte semplicemente i prexxi per una specifica coppia di valute.
        Inverte il bid/ask di "EURUSD" nel bid/ask per "USDEUR"
        e li inserische nel dizionario dei pressi.
        """
        getcontext().rounding = ROUND_HALF_DOWN
        inv_pair = "%s%s" % (pair[3:], pair[:3])
        inv_bid = (Decimal("1.0") / bid).quantize(
            Decimal("0.00001")
        )
        inv_ask = (Decimal("1.0") / ask).quantize(
            Decimal("0.00001")
        )
        return inv_pair, inv_bid, inv_ask

    def connect_to_stream(self):
        pairs_oanda = ["%s_%s" % (p[:3], p[3:]) for p in self.pairs]
        pair_list = ",".join(pairs_oanda)
        try:
            requests.packages.urllib3.disable_warnings()
            s = requests.Session()
            url = "https://" + self.domain + "/v1/prices"
            headers = {'Authorization': 'Bearer ' + self.access_token}
            params = {'instruments': pair_list, 'accountId': self.account_id}
            req = requests.Request('GET', url, headers=headers, params=params)
            pre = req.prepare()
            resp = s.send(pre, stream=True, verify=False)
            return resp
        except Exception as e:
            s.close()
            print("Caught exception when connecting to stream\n" + str(e))


    def stream_to_queue(self):
        response = self.connect_to_stream()
        if response.status_code != 200:
            return
        for line in response.iter_lines(1):
            if line:
                try:
                    dline = line.decode('utf-8')
                    msg = json.loads(dline)
                except Exception as e:
                    self.logger.error(
                        "Caught exception when converting message into json: %s" % str(e)
                    )
                    return
                if "instrument" in msg or "tick" in msg:
                    self.logger.debug(msg)
                    getcontext().rounding = ROUND_HALF_DOWN
                    instrument = msg["tick"]["instrument"].replace("_", "")
                    time = msg["tick"]["time"]
                    bid = Decimal(str(msg["tick"]["bid"])).quantize(
                        Decimal("0.00001")
                    )
                    ask = Decimal(str(msg["tick"]["ask"])).quantize(
                        Decimal("0.00001")
                    )
                    self.prices[instrument]["bid"] = bid
                    self.prices[instrument]["ask"] = ask
                    # Inverte i prezzi (EUR_USD -> USD_EUR)
                    inv_pair, inv_bid, inv_ask = self.invert_prices(instrument, bid, ask)
                    self.prices[inv_pair]["bid"] = inv_bid
                    self.prices[inv_pair]["ask"] = inv_ask
                    self.prices[inv_pair]["time"] = time
                    tev = TickEvent(instrument, time, bid, ask)
                    self.events_queue.put(tev)