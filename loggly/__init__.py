import json

from requests import get, post
from requests.auth import HTTPBasicAuth

# Auth data
token = None
api_token = None
user = None
password = None

# Account info
tokens = None
retention = None
subdomain = None
volume_limit = None

# Exception related stuff
class LogglyError(Exception):
    pass

class AuthenticationError(LogglyError):
    pass

class RequestError(LogglyError):
    def __init__(self, response):
        self.response = response
        self.message = response.text
        self.status_code = response.status_code
        self.reason = response.reason

class InvalidStatError(LogglyError):
    def __init__(self, stat):
        self.stat = stat

# "Private" functions
def __basicauth():
    if user is None or password is None:
        return None
    return HTTPBasicAuth(user, password)

def __apiauth():
    if api_token is None:
        return None
    return { 'Authorization': 'Bearer {}'.format(api_token) }

def __getauth():
    auth = __apiauth()
    if not auth:
        auth = __basicauth()
    return auth


class SearchIterator(object):
    def __init__(self, url, auth, params):
        self.url = url
        self.auth = auth
        self.params = params

    def __iter__(self):
        return self

    def __next__(self):
        if self.url is None: raise StopIteration

        response = SearchIterator.get_page(self.url, self.auth, self.params)
        self.url = response['next'] if 'next' in response else None
        if 'events' in response:
            return response['events']
        return list()

    def get_page(url, auth, params):
        response = None
        # auth can be an API token header dict or a basic auth object; react accordingly
        if isinstance(auth, HTTPBasicAuth):
            response = get(url, auth=auth, params=params)
        elif isinstance(auth, dict):
            response = get(url, headers=auth, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            raise RequestError(response)
        return None


# The "exposed" functions
def account_info():
    global tokens, subdomain, retention, volume_limit

    # Try an API token first; failing that, try HTTPBasicAuth
    auth = __getauth()

    if auth:
        url = 'https://{}.loggly.com/apiv2/customer'.format(subdomain)
        if isinstance(auth, HTTPBasicAuth):
            response = get(url, auth=auth)
        elif isinstance(auth, dict):
            response = get(url, headers=auth)

        print(response.status_code)
        if response.status_code == 200:
            info = response.json()
            tokens = info['tokens']
            subdomain = info['subdomain']
            retention = info['subscription']['retention_days']
            volume_limit = info['subscription']['volume_limit_mb']
            return info
        else:
            raise RequestError(response)
    else:
        raise AuthenticationError()

    return None

def submit(event, tag=None):
    if not token:
        raise AuthenticationError()

    url = 'https://logs-01.loggly.com/inputs/{}/'.format(token)
    if tag:
        url += 'tag/{}'.format(tag)

    content_type = 'text/plain'
    if isinstance(event, dict):
        event = json.dumps(event)
        content_type = 'application/x-www-form-urlencoded'
    if isinstance(event, str):
        try:
            json.loads(event)
            content_type = 'application/x-www-form-urlencoded'
        except ValueError:
            pass

    response = post(
        url,
        headers={'Content-Type': content_type},
        data=event)


    if response.status_code == 200:
        return True
    else:
        raise RequestError(response)

def bulk_submit(events, tag=None):
    if not token:
        raise AuthenticationError()

    url = 'https://logs-01.loggly.com/bulk/{}/'.format(token)
    if tag:
        url += 'tag/{}'.format(tag)

    if isinstance(events, list):
        events = '\n'.join(events)

    print(events)

    response = post(
        url,
        headers={'Content-Type': 'text/plain'},
        data=events)

    if response.status_code == 200:
        return True
    else:
        raise RequestError(response)

def search(query=None, frm=None, til=None, paginate=False, pagesize=None, order=None):
    # Events Retrieval API: https://www.loggly.com/docs/paginating-event-retrieval-api/

    # Try an API token first; failing that, try HTTPBasicAuth
    auth = __getauth()

    if auth:
        baseurl = 'https://{}.loggly.com/apiv2/events/iterate'.format(subdomain)
        events = list()
        params = dict()
        if query: params['q'] = query
        if frm: params['from'] = frm
        if til: params['until'] = til
        if pagesize: params['size'] = pagesize
        if order:
            params['order'] = order if order in [ 'asc', 'desc' ] else None
        if not order: params.pop('order', None)

        url = baseurl

        if paginate:
            return SearchIterator(url, auth, params)
        else:
            while True:
                response = SearchIterator.get_page(url, auth, params)
                if response:
                    if 'events' in response:
                        events.extend(response['events'])
                    if 'next' in response:
                        url = response['next']
                    else:
                        break
            return events
    else:
        raise AuthenticationError()

    return None

def stats(stat='all', field=None, query='*', frm=None, til=None):
    # Validate the stat field
    stat = stat.lower()
    if stat not in [
        'avg',
        'sum',
        'min',
        'max',
        'percentiles',
        'variance',
        'std_deviation',
        'sum_of_squares',
        'count',
        'stats',
        'extended',
        'all' ]:
            raise InvalidStatError(stat)

    auth = __getauth()

    if auth:
        baseurl = 'https://{}.loggly.com/apiv2/stats/{}/{}'.format(subdomain, stat, field)
        params = dict()
        if query: params['q'] = query
        if frm: params['from'] = frm
        if til: params['until'] = til
        if len(params.keys()) > 0:
            url = '{}?{}'.format(baseurl, __format_params(params))
        else:
            url = baseurl

        response = None
        if isinstance(auth, dict):
            response = get(url, headers=auth)
        elif isinstance(auth, HTTPBasicAuth):
            response = get(url, auth=auth)

        if response.status_code == 200:
            return response.json()
        else:
            raise RequestError(response)
    else:
        raise AuthenticationError()

