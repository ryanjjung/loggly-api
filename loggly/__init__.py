import json
import requests

# Auth data
customer_token = None
api_token = None

# Account info
customer_tokens = None
retention = None
subdomain = None
volume_limit = None

# Exception related stuff
class LogglyError(Exception):
    '''
    Base exception with no function outside of identifying the error as one from
    this library.
    '''
    pass

class AuthenticationError(LogglyError):
    '''
    Exception related to authentication with the API
    '''
    pass

class RequestError(LogglyError):
    '''
    Exception that gets raised when the library is able to detect a request
    formation error before the request gets made.
    '''
    def __init__(self, reason):
        self.reason = reason

class ResponseError(LogglyError):
    '''
    Exception that gets raised when an API call results in a bad status code
    '''
    def __init__(self, response):
        self.response = response
        self.message = response.text
        self.status_code = response.status_code
        self.reason = response.reason

# Internally used functions
def get_auth():
    '''
    Returns an appropriate HTTP header for API token authentication
    '''

    if api_token is None: return None
    return { 'Authorization': 'Bearer {}'.format(api_token) }

def call_api(path, method='GET', params=None):
    '''
    Calls the API at the given path, using the given method and query parameters
    '''

    auth = get_auth()
    if auth:
        url = 'https://{}.loggly.com{}'.format(subdomain, path)
        response = requests.request(method, url, headers=auth, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            raise ResponseError(response)
    else:
        raise AuthenticationError()

def get_next_id_from_url(url):
    '''
    The Loggly search pagination endpoint returns a "next" field which contains
    a full URL. Our call_api function wants just the "next" page ID. This
    function extracts that ID so we can take advantage of the error handling and
    other features of the call_api function.
    '''

    try:
        query_str = url.split('?')[1]
    except KeyError:
        return None
    params = query_str.split('&')
    for param in params:
        if param[:5] == 'next=':
            return param[5:]
    return None

class SearchIterator(object):
    '''
    An iterator that handles event search pagination
    '''

    def __init__(self, params):
        self.params = params
        self.next = None

    def __iter__(self):
        return self

    def __next__(self):
        '''
        Get the next page or raise a StopIteration exception
        '''

        params = dict()
        if self.next == '':
            raise StopIteration
        elif self.next is not None:
            self.params['next'] = self.next

        response = call_api('/apiv2/events/iterate', params=self.params)
        if 'next' in response:
            self.next = get_next_id_from_url(response['next'])
        else:
            self.next = ''
        return response['events'] if 'events' in response else list()

# User-intended functions
def account_info():
    '''
    Retrieves account-level metadata and stores it in some convenience variables
    '''

    global customer_tokens, subdomain, retention, volume_limit

    response = call_api('/apiv2/customer')
    customer_tokens = response['tokens']
    subdomain = response['subdomain']
    retention = response['subscription']['retention_days']
    volume_limit = response['subscription']['volume_limit_mb']
    return response

def submit(event, tag=None):
    '''
    Ships a single event to Loggly. `tag` is an optional tag to apply to the event.
    Autodetects what content type to use based on the contnet of `event`.
    '''

    # Don't bother with anything else if we're not authenticated
    if not customer_token:
        raise AuthenticationError()

    # This feature of Loggly's API uses a different URL entirely, so we do not use
    # the call_api convenience function here.
    url = 'https://logs-01.loggly.com/inputs/{}'.format(customer_token)
    if tag:
        url += '/tag/{}'.format(tag)

    # Detect event format
    if isinstance(event, dict):
        event = json.dumps(event)
        content_type = 'application/x-www-form-urlencoded'
    elif isinstance(event, str):
        try:
            json.loads(event)
            content_type = 'application/x-www-form-urlencoded'
        except ValueError:
            content_type = 'text/plain'

    response = requests.post(
        url,
        headers={'Content-Type': content_type},
        data=event)

    if response.status_code == 200:
        return True
    else:
        raise ResponseError(response)

def bulk_submit(events, tag=None):
    '''
    Ships multiple events in a single request. `tag` is an optional tag to apply
    to the events. `events` is a Python list.

    Loggly places limitations on the size of this data. At the time of this
    writing, that's 1 MB per event and 5 MB per HTTP request.

    https://documentation.solarwinds.com/en/Success_Center/loggly/Content/admin/http-bulk-endpoint.htm
    '''

    if not customer_token:
        raise AuthenticationError()

    url = 'https://logs-01.loggly.com/bulk/{}'.format(customer_token)
    if tag:
        url += '/tag/{}'.format(tag)

    if isinstance(events, list):
        events = '\n'.join(events)
    elif not isinstance(events, str):
        raise RequestError('events must be a list or string')

    response = requests.post(
        url,
        headers={'Content-Type': 'text/plain'},
        data=events)

    if response.status_code == 200:
        return True
    else:
        raise ResponseError(response)

def search(query=None, frm=None, til=None, paginate=False, pagesize=None, order=None):
    # Events Retrieval API: https://www.loggly.com/docs/paginating-event-retrieval-api/

    if order and order not in [ 'asc', 'desc' ]:
        raise RequestError('Search order must be "asc" or "desc"')

    events = list()
    params = dict()
    if query: params['q'] = query
    if frm: params['from'] = frm
    if til: params['until'] = til
    if pagesize: params['size'] = pagesize
    if order: params['order'] = order

    searcher = SearchIterator(params)
    if paginate:
        return searcher
    else:
        for page in searcher:
            if 'events' in page:
                events.extend(page['events'])
        return events

def stats(stat='all', field=None, query='*', frm=None, til=None):
    if not field:
        raise RequestError('For stats calls, "field" is required')

    # Validate the stat field
    stat = stat.lower()
    if stat not in [
        'avg',
        'sum',
        'min',
        'max',
        'percentiles',
        'value_count',
        'cardinality',
        'stats',
        'extended',
        'all' ]:
            raise RequestError('{} is not a valid stats option'.format(stat))

    params = dict()
    if query: params['q'] = query
    if frm: params['from'] = frm
    if til: params['until'] = til

    path = '/apiv2/stats/{}'.format(stat)
    if field: path = '{}/{}'.format(path, field)
    return call_api(path, params=params)

def volume_metrics(frm=None, til=None, group_by=None, host=None, app=None, measurement_types=None):
    valid_group_bys = [ 'host', 'app' ]
    valid_measurement_types = [ 'volume_bytes', 'count' ]
    if group_by:
        for gp in group_by:
            if gp not in valid_group_bys:
                return False
    if measurement_types:
        for mt in measurement_types:
            if mt not in valid_measurement_types:
                return False

    params = dict()
    if frm: params['from'] = frm
    if til: params['until'] = til
    if group_by: params['group_by'] = ','.join(group_by)
    if host: params['host'] = host
    if app: params['app'] = app
    if measurement_types: params['measurement_types'] = ','.join(measurement_types)

    return call_api('/apiv2/volume-metrics', params=params)
