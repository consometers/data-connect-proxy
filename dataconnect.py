import requests
import urllib
import json

import datetime as dt
import pytz

class DataConnectError(Exception):
    def __init__(self, message, code=None):
        self.message = message
        self.code = code

    def __str__(self):
        if self.code is not None:
            return f"{self.code}: {self.message}"
        else:
            return self.message

class DataConnect():

    def __init__(self, client_id, client_secret, redirect_uri, sandbox=False):

        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

        if sandbox:
            self.authorize_endpoint = "https://gw.hml.api.enedis.fr"
            self.api_endpoint = "https://gw.hml.api.enedis.fr"
        else:
            self.authorize_endpoint = "https://mon-compte-particulier.enedis.fr"
            self.api_endpoint = "https://gw.prd.api.enedis.fr"

    def make_authorize_url(self, duration, state=None):

        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'duration': duration
        }

        if state is not None:
            params['state'] = state

        params = urllib.parse.urlencode(params)

        return self.authorize_endpoint + '/dataconnect/v1/oauth2/authorize?' + params

    def get_access_token(self, code = None, refresh_token = None):

        params = {'redirect_uri': self.redirect_uri }
        payload = {'client_id': self.client_id, 'client_secret': self.client_secret }

        if code is not None and refresh_token is None:
            payload['grant_type'] = 'authorization_code'
            payload['code'] = code
        elif refresh_token is not None and code is None:
            payload['grant_type'] = 'refresh_token'
            payload['refresh_token'] = refresh_token
        else:
            raise ValueError("Either code or refresh_token has to be provided")

        r = requests.post(self.api_endpoint + "/v1/oauth2/token", params=params, data=payload)
        if r.status_code == 200:
            return r.json()
        else:
            try:
                error = r.json()
                raise DataConnectError(error['error_description'], code=error['error'])
            except (KeyError, json.decoder.JSONDecodeError) as e:
                raise DataConnectError(r.text)

    def get_load_curve(self, direction, usage_point_id, start_date, end_date, access_token):

        if not direction in ['consumption', 'production']:
            raise ValueError(f'Unexpected load curve direction: {direction}')

        start_date = self.date_to_isostring(start_date)
        end_date = self.date_to_isostring(end_date)

        params = {
            'usage_point_id': usage_point_id,
            'start': start_date,
            'end': end_date
        }
        hed = {'Authorization': 'Bearer ' + access_token}

        r = requests.get(f"{self.api_endpoint}/v4/metering_data/{direction}_load_curve", params=params, headers=hed)

        if r.status_code == 200:
            return r.json()
        else:
            try:
                error = r.json()
                raise DataConnectError(error['error_description'], code=error['error'])
            except (KeyError, json.decoder.JSONDecodeError) as e:
                raise DataConnectError(r.text)

    # Cette sous ressource renvoie les valeurs correspondant à la consommation quotidienne (en Wh)
    # sur chaque jour de la période demandée. Chaque valeur est daté. Un appel peut porter sur des
    # données datant au maximum de 36 mois et 15 jours avant la date d’appel.

    def get_daily(self, direction, usage_point_id, start_date, end_date, access_token):

        if not direction in ['consumption', 'production']:
            raise ValueError(f'Unexpected load curve direction: {direction}')

        start_date = self.date_to_isostring(start_date)
        end_date = self.date_to_isostring(end_date)

        params = {
            'usage_point_id': usage_point_id,
            'start': start_date,
            'end': end_date
        }
        hed = {'Authorization': 'Bearer ' + access_token}

        r = requests.get(f"{self.api_endpoint}/v4/metering_data/daily_{direction}", params=params, headers=hed)

        if r.status_code == 200:
            return r.json()
        else:
            try:
                error = r.json()
                raise DataConnectError(error['error_description'], code=error['error'])
            except (KeyError, json.decoder.JSONDecodeError) as e:
                raise DataConnectError(r.text)

    @staticmethod
    def date_to_isostring(date):
        if isinstance(date, dt.date):
            return date.strftime('%Y-%m-%d')
        if isinstance(date, str):
            return date

        raise ValueError(f"Unknown date object: {date}")

    @staticmethod
    def date(date, half_hour_id=None):
        date = dt.datetime.strptime(date, '%Y-%m-%d') + dt.timedelta()

        if half_hour_id is not None:
            date = date + dt.timedelta(minutes=30*int(half_hour_id))

        paris_tz = pytz.timezone('Europe/Paris')
        date = paris_tz.localize(date)
        return date

        #print(paris_tz.localize(date).astimezone(pytz.utc).strftime("%s"))

    @staticmethod
    def datetime(date):
        date = dt.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        paris_tz = pytz.timezone('Europe/Paris')
        date = paris_tz.localize(date)
        return date

        #print(paris_tz.localize(date).astimezone(pytz.utc).strftime("%s"))

TEST_CLIENTS = {
    "0": "Client qui ne possède qu’un seul point de livraison de consommation pour lequel il a activé la courbe de charge. Ses données sont remontées de manière exacte (sans « trou » de données) et son compteur a été mis en service au début du déploiement Linky.",
    "1": "Client qui ne possède qu’un seul point de livraison de consommation pour lequel il a activé la courbe de charge. Ses données sont remontées de manière exacte (sans « trou » de données) et son compteur a été mis en service le 27 août 2019.",
    "2": "Client qui ne possède qu’un seul point de livraison de consommation pour lequel il n’a pas activé la courbe de charge. Ses données sont remontées de manière exacte (sans « trou » de données) et son compteur a été mis en service au début du déploiement Linky.",
    "3": "Client qui possède un point de livraison de consommation et un point de livraison de production pour lesquels il a activé les courbes de charge. Ses données sont remontées de manière exacte (sans « trou » de données) et ses compteurs ont été mis en service au début du déploiement Linky.",
    "4": "Client qui possède qu’un seul point de livraison de consommation pour lequel il a activé la courbe de charge. Ses données présentent des « trous » de données les mardis et mercredis et son compteur a été mis en service au début du déploiement Linky",
    "5": "Client qui possède qu’un seul point de livraison de production pour lequel il a activé la courbe de charge. Ses données sont remontées de manière exacte (sans « trou » de données) et son compteur a été mis en service au début du déploiement Linky.",
    "6": "Client qui possède un point de livraison d’ auto-consommation pour lequel il a activé la courbe de charge en production et en consommation. Pour chaque point prélevé, lorsque la consommation est supérieur à la production les données de consommation remontées correspondent à la consommation moins la production et la production est nulle. Inversement lorsque la production est supérieure à la consommation. Ses données sont remontées de manière exacte (sans « trou » de données) et son compteur a été mis en service au début du déploiement Linky.",
    "7": "Client qui possède trois points de livraison de consommation pour lesquels il a activé les courbes de charge. Ses données sont remontées de manière exacte (sans « trou » de données) et ses compteurs ont été mis en service au début du déploiement Linky.",
    "8": "Client qui donne son consentement mais le révoque immédiatement après l’avoir donné.",
    "9": "Client qui refuse systématiquement de donner son consentement."
}

if __name__ == '__main__':

    import unittest

    class TestDataConnect(unittest.TestCase):

        def test_date_is_parsed_from_iso_format(self):
            date = DataConnect.date('2020-05-22')
            self.assertEqual(date.year, 2020)
            self.assertEqual(date.month, 5)
            self.assertEqual(date.day, 22)
            self.assertEqual(date.hour, 0)
            self.assertEqual(date.minute, 0)
            self.assertEqual(date.second, 0)

        def test_date_is_defined_at_paris_time(self):
            date = DataConnect.date('2020-05-22')
            self.assertEqual(date.utcoffset(), dt.timedelta(hours=2))

        def test_date_half_hour_ids(self):
            date = DataConnect.date('2020-05-22', half_hour_id=1)
            self.assertEqual(date.hour, 0)
            self.assertEqual(date.minute, 30)

            date = DataConnect.date('2020-05-22', half_hour_id=48)
            self.assertEqual(date.day, 23)
            self.assertEqual(date.hour, 0)
            self.assertEqual(date.minute, 0)

        def test_date_to_isostring(self):
            date = DataConnect.date_to_isostring('2020-05-22')
            self.assertEqual(date, '2020-05-22')

            date = DataConnect.date_to_isostring(dt.date(2020, 5, 22))
            self.assertEqual(date, '2020-05-22')

            date = DataConnect.date_to_isostring(dt.datetime(2020, 5, 22, 0, 0))
            self.assertEqual(date, '2020-05-22')

    unittest.main()
