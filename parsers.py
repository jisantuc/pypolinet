from ConfigParser import ConfigParser
import json
import numpy as np
import pandas as pd
import dask
import xray
import matplotlib.pyplot as plt
import oauth2 as oauth
import indicoio

class SingleUser(object):
    """
    Reads followers of a given user and calculates the most likely political
    affiliation of their most recent tweets using the indicoio political
    API.
    """

    def __init__(self, user, path_to_keys, ntweets=200):
        parser = ConfigParser()
        parser.read(path_to_keys)
        keys = dict(parser.items('pypolinet'))
        self.indico = indicoio
        self.indico.config.api_key = keys['indicoio_key']
        self.consumer = oauth.Consumer(
            key=keys['consumer_key'],
            secret=keys['consumer_secret']
        )
        self.access_token = oauth.Token(
            key=keys['access_token'],
            secret=keys['access_secret']
        )
        self.client = oauth.Client(self.consumer, self.access_token)
        self.user = user
        self.ntweets = ntweets

    def _sleep_until(self, future_time):
        return time.ctime(future_time + 1) - time.clock()

    def is_rate_limited(self, service):
        """
        Checks whether a given service is over the rate limit.
        """

        # fill in:
        # endpoint for rate limit check
        endpoint = ''.join([
            'https://api.twitter.com/1.1/application/',
            'rate_limit_status.json?resources={}'.format(service)
        ])

        response = self.client.request(
            uri=endpoint,
            method='GET'
        )[0]

        if response['x-rate-limit-remaining'] > 0:
            return False

        return response

    def read_tweets(self):
        """
        Reads most recents tweets for user.
        """

        endpoint = ''.join([
            'https://api.twitter.com/1.1/statuses/user_timeline.json?',
            'screen_name={NAME}&count={COUNT}'.format(
                NAME=self.user,
                COUNT=self.ntweets
            )
        ])

        #avoid the rate limit by chilling when up against it
        delay = self.is_rate_limited('statuses')
        if delay:
            # find out how long until good and wait that long
            self._sleep_until(delay['x-rate-limit-reset'])

        statuses = json.loads(self.client.request(
            uri=endpoint,
            method='GET'
        )[1])

        out = xray.DataArray(
            [s['text'] for s in statuses[:self.ntweets]],
            coords={'user': [self.user] * self.ntweets},
            dims=['user']
        )
        return out

    def score_tweet(self, tweet):
        """
        Scores a tweet using the indicoio api.
        """

        return self.indico.political(tweet)

    def score_tweets(self, tweets):
        """
        Scores all tweets and returns a labeled array of party affiliations
        by tweet index in list of tweets.
        """

        da = xray.DataArray(
            [self.score_tweet(tweet) for tweet in tweets],
            coords=[tweets.user],
        )
        return xray.DataArray(da)

    def mean_scores(self):
        """
        Returns mean scores indexed by affiliations.
        """

        return self.score_tweets(self.read_tweets()).mean(
            dims=['tweetnum']
        )

    def get_friends(self):
        """
        Returns all friends for self.user
        """

        endpoint = ''.join([
            'https://api.twitter.com/1.1/friends/list.json?',
            'screen_name={NAME}&count=150'.format(NAME=self.user)
        ])
        delay = self.is_rate_limited('friends')
        if delay:
            self._sleep_until(delay['x-rate-limit-reset'])

        response = json.loads(self.client.request(
            uri=endpoint,
            method='GET'
        )[1])

        return [u['screen_name'] for u in response['users']]

class MultiUser(SingleUser):
    """
    Creates SingleUserParser instances for each of several twitter users and
    visualizes their similarity.
    """

    def __init__(self, users, path_to_keys, user=None, ntweets=200):
        SingleUser.__init__(self, user=None, path_to_keys=path_to_keys)
        self.users = users
        self.ntweets = ntweets

