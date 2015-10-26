from ConfigParser import ConfigParser
import time
import calendar
import json
from progress.bar import Bar
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import oauth2 as oauth
import indicoio

class NetworkParser(object):
    """
    Reads followers of a given user and calculates the most likely political
    affiliation of their most recent tweets using the indicoio political
    API.
    """

    def __init__(self, user, path_to_keys, ntweets=200, presleep=False):
        self.path_to_keys = path_to_keys
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

        if presleep:
            time.sleep(self._sleep_until(
                self.rate_limit_response('statuses')['x-rate-limit-reset']
            ))

    def _sleep_until(self, future_time):
        future_time = float(future_time)
        lag = (future_time + 1) - calendar.timegm(time.gmtime())
        print 'Lagging {} minutes'.format(round(lag / 60., 2))
        return lag

    def rate_limit_response(self, service):
        """
        Checks whether a given service is over the rate limit.
        """

        endpoint = ''.join([
            'https://api.twitter.com/1.1/application/',
            'rate_limit_status.json?resources={}'.format(service)
        ])

        response = self.client.request(
            uri=endpoint,
            method='GET'
        )[0]

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

        statuses = json.loads(self.client.request(
            uri=endpoint,
            method='GET'
        )[1])

        if isinstance(statuses, dict):
            return pd.Series()

        if statuses:
            out = pd.Series(
                [s['text'] for s in statuses[:self.ntweets]],
                name=['user']
            )
            return out
        else:
            return pd.Series()

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

        df = pd.DataFrame(
            [self.score_tweet(tweet) for tweet in tweets]
        )

        df.index = pd.MultiIndex.from_tuples(
            zip([self.user] * len(df),
                range(len(df))),
            names=['user', 'tweetnum']
        )

        return df

    def score_tweets_agg(self, tweets):
        """
        Aggregates all tweets into a single corpus and submits to indico
        API for likely party affiliations.
        """

        if len(tweets)==0:
            print 'Zero tweets for {}'.format(self.user)
            return pd.DataFrame()

        corpus = ' '.join(tweets)

        df = pd.DataFrame(
            [self.score_tweet(corpus)],
            index=[self.user]
        )
        df.index.name = 'user'
        return df

    def mean_scores(self, agg=False):
        """
        Returns mean scores indexed by affiliations.
        """

        return self.score_tweets(self.read_tweets()).mean(
            name=['tweetnum']
        ) if not agg else self.score_tweets_agg(self.read_tweets())

    def get_friends(self):
        """
        Returns all friends for self.user
        """

        endpoint = ''.join([
            'https://api.twitter.com/1.1/friends/list.json?',
            'screen_name={NAME}&count=150'.format(NAME=self.user)
        ])
        delay = self.rate_limit_response('friends')
        if delay:
            self._sleep_until(delay['x-rate-limit-reset'])

        response = json.loads(self.client.request(
            uri=endpoint,
            method='GET'
        )[1])

        return [u['screen_name'] for u in response['users']]

    def score_friends(self, friends):
        if not friends:
            raise ValueError('{} has no friends.'.format(self.user))

        users = [
            NetworkParser(u, self.path_to_keys, self.ntweets)
            for u in friends
        ]

        bar = Bar(
            width=40,
            suffix='%(percent)d%%'
        )
        print 'Scoring {}\'s network...'.format(self.user)
        tweet_scores = pd.concat(
            [u.mean_scores(agg=True) for u in bar.iter(users)]
        )

        return tweet_scores.groupby(level='user').mean()
