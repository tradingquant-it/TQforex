from abc import ABCMeta, abstractmethod
import http.client as httplib
from urllib.parse import urlencode
import logging
import urllib3
urllib3.disable_warnings()

class ExecutionHandler(object):
    """
    Fornisce la classe base astratta per gestire tutte le esecuzioni
    nel backtesting e nei sistemi di trading live.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def execute_order(self):
        """
        Inivo dell'ordine al broker
        """
        raise NotImplementedError("Should implement execute_order()")


class SimulatedExecution(object):
    """
    Fornisce un ambiente per la gesione di esecuzioni simulate. In realtà
    questa classe non fa niente - essa riceve semplicemente un ordine da
    eseguire. Invece, è l'oggetto portafoglio che fornisce la gestione
    degli eseguiti.
    Da modificare nella prossima versione
    """
    def execute_order(self, event):
        pass


class OANDAExecutionHandler(ExecutionHandler):
    def __init__(self, domain, access_token, account_id):
        self.domain = domain
        self.access_token = access_token
        self.account_id = account_id
        self.conn = self.obtain_connection()
        self.logger = logging.getLogger(__name__)

    def obtain_connection(self):
        return httplib.HTTPSConnection(self.domain)

    def execute_order(self, event):
        instrument = "%s_%s" % (event.instrument[:3], event.instrument[3:])
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Bearer " + self.access_token
        }
        params = urlencode({
            "instrument" : instrument,
            "units" : event.units,
            "type" : event.order_type,
            "side" : event.side
        })
        self.conn.request(
            "POST",
            "/v1/accounts/%s/orders" % str(self.account_id),
            params, headers
        )
        response = self.conn.getresponse().read().decode("utf-8").replace("\n","").replace("\t","")
        self.logger.debug(response)