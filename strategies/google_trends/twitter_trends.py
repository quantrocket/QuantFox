from TwitterSearch import *
try:
    tso = TwitterSearchOrder() # create a TwitterSearchOrder object
    tso.setKeywords(['FCX', 'Freeport McMoran']) # let's define all words we would like to have a look for
    tso.setLanguage('en') # we want to see German tweets only
    tso.setCount(1) # please dear Mr Twitter, only give us 1 results per page
    tso.setIncludeEntities(False) # and don't give us all those entity information

    # it's about time to create a TwitterSearch object with our secret tokens
    ts = TwitterSearch(
        consumer_key = 'ug5WVZqqCD9vY8gY9SVCQ',
        consumer_secret = 'pr1yfm0oTNbGtZnL1bd5R3Ybl4fr9NteDgDnyjpwaA',
        access_token = '160739524-e0k14cLQGqaQalNKWOhp6QApGGKMYKqJMzZwzohA',
        access_token_secret = 'Ml2mEkEr5FSd8ymcEZrQh5gtwWeQSkvtXekK7GZHQR4'
     )

    ts.authenticate() # we need to use the oauth authentication first to be able to sign messages

    counter  = 0 # just a small counter
    for tweet in ts.searchTweetsIterable(tso): # this is where the fun actually starts :)
        counter += 1
        print '@%s tweeted: %s' % (tweet['user']['screen_name'], tweet['created_at'])#, tweet['date'])

    print '*** Found a total of %i tweets' % counter

except TwitterSearchException, e: # take care of all those ugly errors if there are some
    print e.message