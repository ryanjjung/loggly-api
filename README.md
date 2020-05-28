# loggly-api

## Description

This library allows a user to work with Loggly's APIs through simple function calls.

**Note:** As of version 0.3.0, this library only supports Loggly's API v2 as described
[here](https://documentation.solarwinds.com/en/Success_Center/loggly/Content/admin/api-overview.htm)
Additionally, only API tokens are supported as an authentication type. Username/password (HTTP Basic
Auth) support has been ripped out. Other breaking changes have also been implemented, such as the
change of the `loggly.token` variable to `loggly.customer_token` to be consistent with Loggly's
terminology. `RequestError`s no longer represent responses and are now called `ResponseError`s.
A `RequestError` is now something completely different, and is documented below. `InvalidStatError`
no longer exists, and has been converted into a `RequestError`.

**If your code relies on these features and you cannot update your code, install version 0.2.3 of
this library.**

## Installation

    pip install loggly-api

You're done.

Unless you need an old version, in which case, you should try:

    pip install loggly-api<0.3.0

## Usage

    import loggly

You can set various access credentials; different ones are needed for certain operations.

    loggly.subdomain = 'your_subdomain'
    loggly.customer_token = 'your_customer_token'
    loggly.api_token = 'your_api_token'

### [Ship One Event, or a Multiline Event](https://documentation.solarwinds.com/en/Success_Center/loggly/Content/admin/http-endpoint.htm)

_You need a customer token to ship logs (as opposed to an API token)._

The Content-Type header of the request will be automatically determined, so you can ship JSON by
passing in a dict or a JSON-parseable string. Anything else gets treated as plaintext.

    loggly.submit('Event data')       # Plaintext
    loggly.submit({ 'foo': 'bar' })   # JSON
    loggly.submit('{ "foo": "bar" }') # JSON

All forms of `submit` support tagging the events by setting the `tag=whatever` argument.

    loggly.submit('Event data', tag='production')

### [Ship Bulk Data](https://documentation.solarwinds.com/en/Success_Center/loggly/Content/admin/http-bulk-endpoint.htm)

_You need a customer token to ship logs._

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
single events larger than 1 MB each, and no more than 5 MB per request.

### [Search Events](https://documentation.solarwinds.com/en/Success_Center/loggly/Content/admin/api-retrieving-data.htm)

_To search events, you need a subdomain and an API token._

**Note:** _Loggly has deprecated their single-block retrieval API endpoint, and this library does not
support it. It doesn't matter, though, since the library obscures the method of retrieval and only
presents the outcome of the search._

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
Loggly, try making your page size smaller. The effects of this setting are not always obvious when
`paginate` is `False`, although the page size **is** applied in that case, fewer API calls are made,
and the function may return faster. But when it's `True`, you'll get back that many events at a time
from the iterator.

### [Account Info](https://documentation.solarwinds.com/en/Success_Center/loggly/Content/admin/api-account-info.htm)

Retrieving account info requires a subdomain and an API token.

    info = loggly.account_info()

Calling `account_info()` also updates some convenience properties in the module:

    loggly.customer_tokens
    loggly.retention
    loggly.subdomain
    loggly.volume_limit

### [Statistics](https://documentation.solarwinds.com/en/Success_Center/loggly/Content/admin/stats-api.htm)

The stats API requires a subdomain and either a username/password combo or an API token.

You can call the `stats` function to get statistical data about numerical fields in your log events.
In the fictional example below, you'd get back the average request time for your app.

    stats = loggly.stats(stat='avg', field='json.log.request_time', query='*', frm=None, til=None)

Refer to the [documentation](https://documentation.solarwinds.com/en/Success_Center/loggly/Content/admin/stats-api.htm)
for a complete list of valid statistics you can call for.

## Exceptions

The base class for all exceptions in this module is `loggly.LogglyError`, but it's nothing special
and is useless except to verify that some other error is a loggly error.

    print(isinstance(loggly.RequestError, loggly.LogglyError))

    Output:
      True

A `ResponseError` is thrown anytime this module makes a request to Loggly and gets something other
than a `200 OK` in response. It will contain a `requests` response object as well as some
convenience members which are extracted from it:

    try:
        stats = loggly.stats(field='json.log.bleh')
    except loggly.ResponseError as e:
        print('{} {}\n{}'.format(e.status_code, e.reason, e.message))

    Output:
     400 BAD REQUEST
     The requested field 'json.log.bleh' is unknown.

A `RequestError`, by contrast, is thrown when the library is able to detect a problem in the
formation of a request before the request is made. It contains a `reason` field which will contain
a plaintext explanation of the problem.

    try:
        loggly.bulk_submit({'adict': 'is invalid here'})
    except loggly.RequestError as e:
      print(e.reason)

    Output:
      events must be a list or string

An `AuthenticationError` is raised when you try to make an API call without providing sufficient
credentials for the operation.

    try:
        loggly.subdomain = 'mysub'
        events = loggly.search()
    except AuthenticationError as e:
        print('You didn't set an api_token!')
