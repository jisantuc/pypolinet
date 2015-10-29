import argparse
import glob
from socket import error as SocketError
import pandas as pd
from pandas.tools.plotting import parallel_coordinates
import matplotlib.pyplot as plt
from parsers import NetworkParser

def run_user(user, presleep):
    if len(glob.glob('tweet_data/{}*agg.csv'.format(user))) == 0:
        nparser = NetworkParser(user, 'KEYS', 200, presleep=presleep)
        selfmean = nparser.mean_scores(agg=True)
        selfmean.to_csv('tweet_data/{}_self_agg.csv'.format(user))
        try:
            friendscores = nparser.score_friends(nparser.get_friends())
            friendscores.to_csv(
                'tweet_data/{}_friends_agg.csv'.format(user)
            )
        except SocketError:
            run_user(user, presleep)
    else:
        try:
            selfmean = pd.read_csv(
                'tweet_data/{}_self_agg.csv'.format(user),
                 usecols=[
                     'Conservative', 'Green', 'Liberal',
                     'Libertarian', 'user'
                 ]
            )
            friendscores = pd.read_csv(
                'tweet_data/{}_friends_agg.csv'.format(user),
                usecols=[
                    'Conservative', 'Green', 'Liberal', 'Libertarian',
                    'user'
                ]
            )
        except IOError:
            return

    fig, ax = plt.subplots(figsize=(8,6))
    vals = selfmean.loc[[selfmean.index[0]] * len(friendscores)]
    distances = (
        (friendscores[
            ['Conservative', 'Green', 'Liberal', 'Libertarian']
        ] - vals[
            ['Conservative', 'Green', 'Liberal', 'Libertarian']
        ].values) ** 2
    ).sum(axis=1)
    hold_out_min = distances.idxmin()
    hold_out_max = distances.idxmax()
    parallel_coordinates(
        friendscores.loc[~friendscores.index.isin(
            [hold_out_min, hold_out_max]
        )],
        'user',
        ax=ax,
        color='b',
        **{'alpha': 0.1}
    )
    parallel_coordinates(
        friendscores.loc[[hold_out_min]],
        'user',
        ax=ax,
        color='g',
        **{'alpha': 0.8,
           'label': '\n'.join(
               [friendscores.loc[hold_out_min, 'user'],
                'Most similar']
           )}
    )
    parallel_coordinates(
        friendscores.loc[[hold_out_max]],
        'user',
        ax=ax,
        color='r',
        **{'alpha': 0.8,
           'label': '\n'.join(
               [friendscores.loc[hold_out_max, 'user'],
                'Least similar']
           )}
    )
    parallel_coordinates(
        selfmean,
        'user',
        ax=ax,
        color='k',
        **{'label': user,
           'linestyle': 'dashed'}
    )
    ax.legend()
    ax.set_title('Alignments for {}\'s network'.format(user))
    plt.savefig('plots/{}polinet.png'.format(user))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('users', nargs='*',
                        help='Users whose networks you want to analyze')
    args = parser.parse_args()

    for i, user in enumerate(args.users):
        run_user(user, presleep=(i!=0))
