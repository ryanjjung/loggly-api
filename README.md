# loggly-api

## Description

This library allows a user to work with Loggly's APIs through simple function calls.

## Installation

    pip install loggly-api

You're done.

## Usage

    import loggly

You can set various access credentials; different ones are needed for each operation.

    loggly.token = 'your_customer_token'
    loggly.api_token = 'your_api_token'
    loggly.user = 'your_username'
    loggly.password = 'your_password'
    loggly.subdomain = 'your_subdomain'

### [Ship One Event, or a Multiline Event](https://www.loggly.com/docs/http-endpoint/)

You need a customer token to ship logs (as opposed to an API token).

The Content-Type header of the request will be automatically determined, so you can ship JSON by
passing in a dict or a JSON-parseable string. Anything else gets treated as plaintext.

    loggly.submit('Event data')       # Plaintext
    loggly.submit({ 'foo': 'bar' })   # JSON
    loggly.submit('{ "foo": "bar" }') # JSON

### [Ship Bulk Data](https://www.loggly.com/docs/http-bulk-endpoint/)

You need a customer token to ship logs.

You can pass in a list of events...

    loggly.bulk_submit([
        'Event one',
        'Event two',
        'Event three'])

 ...or a single string.

    with open('/path/to/a/big/log.file', 'r') as fh:
        loggly.bulk_submit(fh.read())

Both forms support tagging.

    loggly.bulk_submit(eventlist, tag='production')

Bear in mind there are restrictions to bulk shipping. At the time of this writing, you can't send
events more than 1MB each, and no more than 5MB per request.

### [Search Events](https://www.loggly.com/docs/api-retrieving-data/)

To search events, you need a subdomain and either a username/password combo or an API token.

You can start a search like this, and the process will hang until search results are returned by the
API, at which point you'll have a list of events:

    events = loggly.search('foo:"bar"', frm='-1D', til='now')

Or you can set `paginate=True` to instead get a SearchIterator back immediately. Each "next" call
will cause a request for more results to come from Loggly. This is essentially a less-automated way
of accomplishing the same thing as above, except you can run other code between pages of results.
Consider:

    search = loggly.search('foo:"bar"', frm='-1D', til='now', paginate=True, pagesize=100)
    events = list()
    for page in search:
        events.extend(page)
        print('{} events collected so far!'.format(len(events)))

`pagesize` is the number of results to return per page. Loggly limits this to 1,000 events at most,
but this can sometimes cause problems as well. If you find yourself getting inexplicable errors from
Loggly, try making your page size smaller. The effects of this setting are pretty transparent when
`paginate` is `False`, although the page size **is** applied in that case. But when it's `True`,
you'll get back that many events at a time from the iterator.

### [Account Info](https://www.loggly.com/docs/api-account-info/)

Retrieving account info requires a subdomain and either a username/password combo or an API token.

    info = loggly.account_info()

Calling `account_info()` also updates some convenience properties in the module:

    loggly.customer_tokens
    loggly.retention
    loggly.subdomain
    loggly.volume_limit

### [Statistics](https://www.loggly.com/docs/stats-api/)

The stats API requires a subdomain and either a username/password combo or an API token.

Then you can call the `stats` function to get the data you need. In the fictional example below,
you'd get back the average request time for your app.

    stats = loggly.stats(stat='avg', field='json.log.request_time', query='*', frm=None, til=None)

Refer to the [documentation](https://www.loggly.com/docs/stats-api/) for a complete list of valid
statistics you can call for.

## Exceptions

The base class for all exceptions in this module is `loggly.LogglyError`, but it's nothing special
and is useless except to verify that some other error is a loggly error.

    print(isinstance(loggly.RequestError, loggly.LogglyError))

    Output:
      True

A `RequestError` is thrown anytime this module makes a request to Loggly and gets something other
than a `200 OK` in response. It will contain a `requests` response object as well as some
convenience members which are extracted from it:

    try:
        stats = loggly.stats(field='json.log.bleh')
    except loggly.RequestError as e:
        print('{} {}\n{}'.format(e.status_code, e.reason, e.message))

    Output:
     400 BAD REQUEST
     The requested field 'json.log.bleh' is unknown.

An `InvalidStatError` is raised when you call `stats()` and provide an invalid stat value.

    try:
        stats = loggly.stats(field='json.log.rq _size', stat='avf')
    except InvalidStatError as e:
        print('Invalid statistic: {}'.format(e.stat))

    Output:
      Invalid statistic: avf

An `AuthenticationError` is raised when you try to make an API call without providing sufficient
credentials for the operation.

    try:
        loggly.subdomain = 'mysub'
        loggly.user = 'myuser'
        events = loggly.search()
    except AuthenticationError as e:
        print('You didn't set a password or an api_token!')

