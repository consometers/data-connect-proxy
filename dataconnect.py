import requests
import urllib

class DataConnectError(Exception):
    pass

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

    def make_authorize_url(self, duration, state = ""):

        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'state': state,
            'duration': duration
        }
        params = urllib.parse.urlencode(params)

        return self.authorize_endpoint + '/dataconnect/v1/oauth2/authorize?' + params

    def get_access_token(self, code = None, refresh_token = None):

        params = {'redirect_uri': self.redirect_uri }
        payload = {'client_id': self.client_id, 'client_secret': self.client_secret }

        print(params)
        print(payload)

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
            raise DataConnectError(r.text)

    def get_consumption_load_curve(self, usage_point_id, start_date, end_date, access_token):

        params = {
            'usage_point_id': usage_point_id,
            'start': start_date,
            'end': end_date
        }
        hed = {'Authorization': 'Bearer ' + access_token}

        r = requests.get(self.api_endpoint + "/v3/metering_data/consumption_load_curve", params=params, headers=hed)

        if r.status_code == 200:
            return r.json()
        else:
            raise DataConnectError(r.text)