# loggly-api

## Description

This library allows a user to work with the Loggly API - including account management, log shipping,
and event retrieval - through simple function calls.

## Usage

    # Imports
    import json
    import loggly
    
    # Configure
    loggly.customer_token = 'your_customer'
    loggly.user = 'your_username'
    loggly.password = 'your_password'

    # Ship logs
    loggly.submit('Event data')
    loggly.submit(json.dumps({ 'foo': 'bar' }))
    
    # Bulk submission
    with open('/path/to/a/big/log.file', 'r') as fh:
        loggly.bulk_submit(fh.read())

    # Search logs/event retrieval

    # Do a search for events, get a list back when the search is done
    events = loggly.search('foo:"bar"', from='-1D', until='now')

    # With paginate=True, you get an iterator instead. Each page will return after the Loggly
    # request completes. Use this if you want to monitor progress or manually page through the data.
    search = loggly.search('foo:"bar"', from='-1D', until='now', paginate=True, pagesize=100)
    events = list()
    for page in search:
        events.extend(events)

    # Get all account info
    loggly.account_info()

    # Convenience access to parts of the account info
    loggly.customer_tokens
    loggly.subdomain
    loggly.volume_limit
    loggly.retention

