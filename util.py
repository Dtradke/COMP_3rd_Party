'''
Author: David Radke
Date: April 25, 2021
'''

import re, tweepy, datetime, time, csv
from tweepy import OAuthHandler
from textblob import TextBlob
import matplotlib.pyplot as plt
import pandas as pd
import urllib.request as rq
import numpy as np
import json
import os

def loadData(url, path):
    if os.path.exists(path):
        with open(path, 'r') as fp:
            dataset = json.load(fp)
    else:
        try:
            dataset = rq.urlopen(url)
            dataset = dataset.read()
            dataset = json.loads(dataset)
        except Exception as e:
            print('Unable to get data from flipsidecrypto API. Check the URL below: \n{}'.format(url))

            with open(path, 'w') as fp:
                json.dump(dataset, fp)

    dates = []
    price, time = [], []
    year, month, day, hour = [], [], [], []
    for i, val in enumerate(dataset):
        # print(val["BLOCK_HOUR"])
        dates.append(val["BLOCK_HOUR"])
        year.append(int(val["BLOCK_HOUR"][:4]))
        price.append(float(val["COMP_PRICE"]))
        time.append(val["BLOCK_HOUR"])
        hour.append(int(val["BLOCK_HOUR"][11:13]))
        day.append(int(val["BLOCK_HOUR"][8:10]))
        month.append(val["BLOCK_HOUR"][5:7])

    year = np.array(year)
    month = np.array(month)
    hour = np.array(hour)
    day = np.array(day)
    price = np.array(price)

    day_dict = {}
    for i in range(np.amin(day), np.amax(day)):
        today_year = year[day==i]
        today_month = month[day==i]
        today_hours = hour[day == i]
        today_day = day[day==i]
        today_prices = price[day == i]
        p = today_hours.argsort()
        sorted_hours = today_hours[p]
        sorted_prices = today_prices[p]
        day_dict[i] = {'year': today_year[0], 'month':today_month[0], 'hours':sorted_hours, 'prices':sorted_prices, 'tweets':[]}

    return day_dict

# Function to clean and line-up data
def matchTweetsPrices(day_dict, tweets_df, get_sentiment=False):
    tweet_amt = {}
    tweet_reach = {}
    tweet_sentiment_dict = {}
    for i in day_dict.keys():
        day = str(i).zfill(2)
        tweet_timestamp = str(day_dict[i]['year'])+str(day_dict[i]['month'])+day
        tweet_timestamp = int(tweet_timestamp)

        tweet_dates = np.array(tweets_df['date'])
        tweet_amt[i] = np.count_nonzero(tweet_dates == tweet_timestamp)

        followers = np.array(tweets_df['followers'])
        tweet_reach[i] = np.sum(followers[tweet_dates == tweet_timestamp])

        if get_sentiment:
            tweet_sentiments = np.array(tweets_df['sentiment'])
            try:
                tweet_sentiment_dict[i] = round(np.mean(tweet_sentiments[(tweet_dates == tweet_timestamp) & (tweet_sentiments != 0)]),2)
            except:
                tweet_sentiment_dict[i] = 0

    return day_dict, tweet_amt, tweet_sentiment_dict, tweet_reach

# function to plot our data. This will be used for multiple aspect of price and twitter data
def plotTweetAmts(day_dict, tweet_char, username, sentiment=False, reach=False):
    fig=plt.figure(figsize=(10, 6))
    prices = []
    for i, val in enumerate(day_dict.keys()):
        if i > 0:
            prices.append(day_dict[val]["prices"])

    prices = np.concatenate(prices, axis=0)

    N = 3
    width = 1
    ind = np.arange(N)
    vals = list(tweet_char.values())[1:]

    plt.bar(ind, vals, width, color='b', edgecolor='k', tick_label=list(tweet_char.keys())[1:], align='center', label='Tweets')

    if sentiment: plt.ylabel("Mean Tweet Sentiment", fontsize=18)
    elif reach: plt.ylabel("Reach of Tweets", fontsize=16)
    else: plt.ylabel("Number of Tweets", fontsize=16)

    plt.xlabel("Days of April", fontsize=16)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)

    ax2 = plt.twinx()
    x = np.linspace(-0.5,2.5, prices.shape[0])
    ax2.plot(x, prices, color='r', linewidth=7, label='COMP Price')
    # ax2.set_ylim(-1, 1)
    ax2.set_ylabel('Price of COMP (USD)', rotation=270, fontsize=16, labelpad=20)
    ax2.tick_params(axis='y', labelsize=14, colors='red')

    if sentiment: plt.title(username+" Tweets Sentiment Effect on COMP Price", fontsize=18)
    elif reach: plt.title("Reach (Followers) of COMP Tweets Effect on COMP Price", fontsize=18)
    else: plt.title(username+" Tweet Amount Effect on COMP Price", fontsize=18)

    plt.legend()
    plt.show()



# Create twitter client class
class TwitterClient(object):

    def __init__(self):
#         need to add your own keys here for the Twitter API
        consumer_key = ""
        consumer_secret = ""
        access_token = ""
        access_token_secret = ""

        try:
            self.auth = OAuthHandler(consumer_key, consumer_secret)
            self.auth.set_access_token(access_token, access_token_secret)
            self.api = tweepy.API(self.auth)

        except:
            print("Error: Authentication Failed")

    def clean_tweet(self, tweet):
        '''
        Cleans the tweet text
        '''
        return ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", tweet).split())

    def get_tweet_sentiment(self, tweet):
        '''
        Uses TextBlob to collect sentiment of tweet, assigns real number label:
        negative = -1,
        neutral = 0,
        positive = 1
        '''
        # create TextBlob object of passed tweet text
        analysis = TextBlob(self.clean_tweet(tweet))
        # set sentiment
        if analysis.sentiment.polarity > 0:
            return 1
        elif analysis.sentiment.polarity == 0:
            return 0
        else:
            return -1

    def getUserTweets(self, username, count=10):
        try:
            # Creation of query method using parameters
            tweets = tweepy.Cursor(self.api.user_timeline,id=username).items(count)

            # Pulling information from tweets iterable object
            tweets_list = []
            for tweet in tweets:
                timestamp = str(tweet.created_at).split(" ")
                sep = ""
                tweet_date = int(sep.join(timestamp[0].split("-")))
                time_clock = timestamp[1]
                tweets_list.append([tweet_date, time_clock, tweet.id, tweet.user.followers_count, tweet.text])
            # tweets_list = [[tweet.created_at, tweet.id, tweet.text] for tweet in tweets]

            # Creation of dataframe from tweets list
            # Add or remove columns as you remove tweet information
            tweets_df = pd.DataFrame(tweets_list)
        except BaseException as e:
            print('failed on_status,',str(e))
            time.sleep(3)

        return tweets_df

    def getTextSearchTweets(self, text_query, count=1000):
        today = datetime.datetime.now()
        today = today.replace(hour=23, minute=59, second=59, microsecond=999999) # set from the beggining of the day
        tweets_df = pd.DataFrame(columns = ['date','time', 'id', 'followers', 'tweet', 'sentiment'])

        week = np.arange(8)
        for d in week:
            time_to_the_past = int(d)
            yesterday = today - datetime.timedelta(time_to_the_past)
            # next_day = yesterday + datetime.timedelta(time_to_the_past) # equivalent to today

            try:
                # Creation of query method using parameters
                tweets = tweepy.Cursor(self.api.search,q=text_query,until = yesterday.date()).items(count)

                # Pulling information from tweets iterable object
                tweets_list = []
                for tweet in tweets:
                    timestamp = str(tweet.created_at).split(" ")
                    sep = ""
                    tweet_date = int(sep.join(timestamp[0].split("-")))
                    time_clock = timestamp[1]
                    tweets_df.loc[len(tweets_df)] = [tweet_date, time_clock, tweet.id, tweet.user.followers_count, tweet.text, self.get_tweet_sentiment(tweet.text)]


            except BaseException as e:
                print('failed on_status,',str(e))
                time.sleep(3)

        return tweets_df

def loadTextTweets(api, path, count, txt_to_query='$COMP'):
    if os.path.exists(path):
        tweets_df = pd.read_csv(path, index_col=0)
    else:
        tweets_df = api.getTextSearchTweets(text_query=txt_to_query, count=count)
        tweets_df.columns = ['date','time', 'id', 'followers', 'tweet', 'sentiment']
        tweets_df.to_csv("data/COMP_tweets"+str(count)+".csv")
    return tweets_df
