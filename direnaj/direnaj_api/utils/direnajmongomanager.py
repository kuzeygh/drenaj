import time

import pymongo
from pymongo import MongoClient

from direnaj_api.config.config import *
from utils.drnj_time import py_utc_time2drnj_time, drnj_time2py_time, now_in_drnj_time, xdays_before_now_in_drnj_time


mongo_client = MongoClient(MONGO_HOST, MONGO_PORT)

db = mongo_client[DIRENAJ_DB[DIRENAJ_APP_ENVIRONMENT]]
queue_coll = db['queue']
graph_coll = db['graph']
tweets_coll = db['tweets']
histograms_coll = db['histograms']
campaigns_coll = db['campaigns']
watchlist_coll = db['watchlist']
pre_watchlist_coll = db['pre_watchlist']

colls = {
    'campaigns': db["freq_campaigns"],
    'tokens': db["freq_tokens"],
    'hashtags': db["freq_hashtags"],
    'mentions': db["freq_mentions"],
    'urls': db["freq_urls"],
    'medias': db["freq_medias"],
    'histograms': db['histograms'],
}

# INDEXES
#

tweets_coll.create_index([('campaign_id', pymongo.ASCENDING), ('tweet.created_at', pymongo.ASCENDING)])
tweets_coll.create_index([('record_retrieved_at', pymongo.ASCENDING)])
tweets_coll.create_index([('campaign_id', pymongo.ASCENDING), ('tweet.user.id_str', pymongo.ASCENDING), ('tweet.user.history', pymongo.ASCENDING)])
tweets_coll.create_index([('tweet.user.id_str', pymongo.ASCENDING), ('tweet.user.history', pymongo.ASCENDING)])

histograms_coll.create_index([('campaign_id', pymongo.ASCENDING), ('created_at', pymongo.ASCENDING)])

campaigns_coll.ensure_index([("campaign_id", 1)], unique=True)

graph_coll.create_index([('id_str', pymongo.ASCENDING), ('following', pymongo.ASCENDING)])
graph_coll.create_index([('friend_id_str', pymongo.ASCENDING), ('following', pymongo.ASCENDING)])

watchlist_coll.create_index([('user.id_str', pymongo.ASCENDING)], unique=True)
watchlist_coll.create_index([('state', pymongo.ASCENDING), ('updated_at', pymongo.DESCENDING)])
watchlist_coll.create_index([('campaign_ids', pymongo.ASCENDING), ('state', pymongo.ASCENDING), ('updated_at', pymongo.DESCENDING)])

pre_watchlist_coll.create_index([('user.id_str', pymongo.ASCENDING)])
pre_watchlist_coll.create_index([('state', pymongo.ASCENDING)])

for key in colls.keys():
    colls[key].create_index([('campaign_id', pymongo.ASCENDING), ('date', pymongo.ASCENDING), ('key', pymongo.ASCENDING)])


def prepare_users_to_be_added(user_id_strs_to_follow, type='id_str'):
    print user_id_strs_to_follow
    lines = user_id_strs_to_follow.split('\n')
    users_to_be_added = []
    for line in lines:
        user = dict()
        if type == 'id_str':
            user = {'user': {'id_str': line, 'screen_name': ''}}
        else:
            user = {'user': {'id_str': '', 'screen_name': line}}
        users_to_be_added.append(user)
    return users_to_be_added
    # lines = user_id_strs_to_follow.split('\n')
    # print lines
    # users_to_be_added = []
    # for line in lines:
    #     line_els = [l.strip() for l in line.split(',')]
    #     print line_els
    #     # first element must be user_id_str
    #     # second element is optional. it should be the username for easier management by humans.
    #     users_to_be_added.append(line_els[0])


def add_to_watchlist(campaign_id, user_id_strs_to_follow, user_screen_names_to_follow):
    users_to_be_added = prepare_users_to_be_added(user_id_strs_to_follow)
    users_to_be_added.append(prepare_users_to_be_added(user_screen_names_to_follow, type='screen_name'))

    for user in users_to_be_added:
        doc = {'user': user['user'],
               'page_not_found': 0, # 0, no problem, 1, problem.
               'since_tweet_id': -1,
               'state': 0, # 0, inqueue, 1, processing
               'added_at': now_in_drnj_time(),
               'updated_at': 0, # 00000101T00:00:00
               'campaign_ids': [campaign_id],
        } # page_not_found: 0, no problem, 1, protected, 2, suspended, 3, other reasons.
        print doc
        ret = watchlist_coll.find_one({'user.id_str': user['user']['id_str']})
        if ret:
            watchlist_coll.update({'_id': ret['_id']}, {'$addToSet': {'campaign_ids': campaign_id}})
            continue
        else:
            ret = watchlist_coll.find_one({'user.screen_name': user['user']['screen_name']})
            if ret:
                watchlist_coll.update({'_id': ret['_id']}, {'$addToSet': {'campaign_ids': campaign_id}})
                continue
        pre_watchlist_coll.insert(doc)
        # try:
        #     # user.id_str field is unique, so it will fail if it exists.
        #     watchlist_coll.insert(doc)
        # # TODO: explore OperationFailure here.
        # except Exception, e:
        #     # TODO: addToSet.
        #     watchlist_coll.find_and_modify({'user.id_str': user['id_str']},{'$push': {'campaign_ids': campaign_id}})
    return True


from direnaj_api.celery_app.server_endpoint import app_object

def create_batch_from_watchlist(n_users):
    docs = pre_watchlist_coll.find({'state': 0}, fields=['user', 'since_tweet_id', 'page_not_found']).limit(n_users)
    pre_watchlist_coll.update({'_id': {'$in': [d['_id'] for d in docs]}}, {'$set': {'state': 1}}, multi=True)
    batch_array = [[d['user'], d['since_tweet_id'], d['page_not_found']] for d in docs]
    left_capacity = n_users - len(batch_array)
    if left_capacity > 0:
        docs = watchlist_coll.find({'state': 0,
                                    'updated_at': {'$lt': xdays_before_now_in_drnj_time(1)}},
                                   fields=['user', 'since_tweet_id', 'page_not_found'])\
            .sort([('updated_at', 1)])\
            .limit(left_capacity)
        watchlist_coll.update({'_id': {'$in': [d['_id'] for d in docs]}}, {'$set': {'state': 1}}, multi=True)
        batch_array += [[d['user'], d['since_tweet_id'], d['page_not_found']] for d in docs]
    ### Now, use this batch_array to call TimelineRetrievalTask.
    res = app_object.send_task('timeline_retrieve_userlist',[batch_array])
    # docs = watchlist_coll.find({'state': 0,
    #                             'updated_at': {'$lt': xdays_before_now_in_drnj_time(1)}},
    #                             ['user.id_str', 'since_tweet_id', 'page_not_found']).sort([('updated_at', 1)]).limit(n_users)
    # id_str_array = [d['user']['id_str'] for d in docs]
    # watchlist_coll.update({'user.id_str': {'$in': id_str_array}}, {'$set': {'state': 1}}, multi=True)
    # batch_array = [[d['user']['id_str'], d['since_tweet_id'], d['page_not_found']] for d in docs]
    # ### Now, use this batch_array to call TimelineRetrievalTask.
    # res = app_object.send_task('timeline_retrieve_userlist',[batch_array])

def update_watchlist(user, since_tweet_id, page_not_found):
    doc = pre_watchlist_coll.find_one({'user.id_str': user['id_str'], 'state': 1})
    if not doc:
        doc = pre_watchlist_coll.find_one({'user.screen_name': user['screen_name'], 'state': 1})
    if doc:
        pre_watchlist_coll.remove({'_id': doc['_id']})
        del doc['_id']
    else:
        doc = watchlist_coll.find_one({'user.id_str': user['id_str'], 'state': 1})
        # required for concurrency. at least I think so.
        if doc:
            pass
        else:
            return
    doc['user'] = user['user']
    doc['since_tweet_id'] = since_tweet_id
    doc['page_not_found'] = page_not_found
    doc['updated_at'] = now_in_drnj_time()
    doc['state'] = 0
    watchlist_coll.update({'user.id_str': doc['user']['id_str']}, doc, upsert=True)
    # watchlist_coll.update({'user.id_str': user_id_str}, {'$set': {'since_tweet_id': since_tweet_id,
    #                                                               'page_not_found': page_not_found,
    #                                                               'updated_at': now_in_drnj_time()}})

def create_campaign(params):
    created_at = now_in_drnj_time()
    params.update({'created_at': created_at})
    user_id_strs_to_follow = str(params["user_id_strs_to_follow"])
    user_screen_names_to_follow = str(params["user_screen_names_to_follow"])
    # removing it to be used elsewhere
    params.pop("user_screen_names_to_follow", None)
    add_to_watchlist(params['campaign_id'], user_id_strs_to_follow, user_screen_names_to_follow)
    campaigns_coll.insert(params)

def get_campaign(campaign_id):
    cursor = campaigns_coll.find({'campaign_id': campaign_id})
    return cursor

def get_campaigns_list():
    cursor = campaigns_coll.find({})
    return cursor

def get_campaign_list_with_freqs(skip, limit):
#    cursor = db.freq_campaigns.aggregate({"$group": { "campaign_id": "$key", "totalTweets": {"$sum": "$day_total"}}})
    cursor = colls["campaigns"].aggregate(
        [{"$group": { "_id": "$key", "total": {"$sum": "$day_total"}, "last_date": {"$max": "$date"}}},
         {"$sort": {"last_date": -1, "total": -1}}, {"$skip": skip},
         {"$limit": limit}])
    return cursor['result']

def get_campaign_with_freqs(campaign_id):
#        [{"$match": {"campaign_id": campaign_id, "date": today}},
    today = time.strftime('%Y-%m-%d', time.gmtime())
    cursor = colls['campaigns'].aggregate(
        [{"$match": {"campaign_id": campaign_id}},
         {"$sort": {"date": -1}}, {"$limit": 1},
         {"$project": {"campaign_id": 1, "date": 1, "series": {"hour": "$hour", "minute": "$minute"}}}])
    return cursor['result']

def calculate_campaign_histograms(campaign_id, n_bins=100):

    n_bins = int(n_bins)

    import matplotlib.pyplot as plot

    plotGraphs = False

    #######
    import numpy
    campaign_query = {'campaign_id': campaign_id}

    projection_query = {'tweet.user.id_str': 1,
                        'tweet.user.default_profile_image': 1,
                        'tweet.user.profile_image_url': 1,
                        'tweet.user.created_at': 1,
                        'tweet.user.followers_count': 1,
                        'tweet.user.friends_count': 1,
                        'tweet.user.statuses_count': 1,
                        'tweet.user.utc_offset': 1,
                        'tweet.user.lang': 1,
                        'tweet.user.timezone': 1,
                        }

    group_query = {'_id': '$tweet.user.id_str',
                'n_user_tweets': {'$sum': 1},
                'user': {'$first': '$tweet.user'}}

    pipeline = [{'$match': campaign_query},
                {'$project': projection_query},
                {'$group': group_query}]

    tmp = tweets_coll.aggregate(pipeline)
    users = tmp['result']

    hist = {
        'user_creation': {
            'data': None,
            'bins': None,
        },
        'user_n_tweets': {
            'data': None,
            'bins': None,
        },
        'user_n_tweets_overall': {
            'data': None,
            'bins': None,
        },
        'n_tweets': None,
        'n_unique_users': None,
        'n_default_profile_image': None,
        'n_lower_than_threshold': None,
    }

    # How many tweets?
    n_tweets = tweets_coll.find(campaign_query).count()
    print "How many tweets? %d" % n_tweets
    hist['n_tweets'] = n_tweets

    # TODO: abort if there are more than 200000 tweets.
    if n_tweets > 200000:
        return hist
    #
    # How many unique users?
    #
    n_unique_users = len(users)
    print "How many unique users? %d" % n_unique_users
    hist['n_unique_users'] = n_unique_users

    ######
    sec_title = "Histogram of user creation dates?"
    #

    tmp_dates = []
    for x in users:
        tmp_date = x['user']['created_at']
        if type(tmp_date) != float:
            tmp_date = py_utc_time2drnj_time(tmp_date)
        tmp_dates.append(tmp_date)
#    tmp_dates = [py_utc_time2drnj_time(x['user']['created_at']) for x in users]

    (hist['user_creation']['data'], hist['user_creation']['bins']) = numpy.histogram(tmp_dates, bins=n_bins)

    if plotGraphs:
        bins = hist['user_creation']['bins'][:-1]
        width = (hist['user_creation']['bins'][1] - hist['user_creation']['bins'][0])/2
        plot.bar(bins, hist['user_creation']['data'], width=width, align='center')

        xticklabels = [time.strftime('%d %b %Y', time.gmtime(drnj_time2py_time(x))) for x in bins]

        plot.xticks(bins, xticklabels)
        plot.title(sec_title)
        #plot.show()
        plot.savefig('1.pdf', dpi=600)

    #####
    sec_title = "Histogram of number of tweets of each user in this campaign"
    tmp_counts = [int(x['n_user_tweets']) for x in users]
    #
    (hist['user_n_tweets']['data'], hist['user_n_tweets']['bins']) = numpy.histogram(tmp_counts, bins=n_bins)

    if plotGraphs:
        bins = hist['user_n_tweets']['bins'][:-1]
        data = hist['user_n_tweets']['data']
        width = (hist['user_n_tweets']['bins'][1] - hist['user_n_tweets']['bins'][0])/2
        plot.bar(bins, data, width=width, align='center')

        xticklabels = bins

        plot.xticks(bins, xticklabels)
        plot.title(sec_title)
        #plot.show()
        plot.savefig('2.pdf', dpi=600)

    #####
    sec_title = "What percentage of them used the default profile image?"
    #
    n_default_profile_image = 0
    for u in users:
        if u['user']['default_profile_image'] == True:
            n_default_profile_image += 1

    hist['n_default_profile_image'] = n_default_profile_image
    print "%s: %0.2f%%" % (sec_title, 100*(float(n_default_profile_image)/n_unique_users))
    #####
    sec_title = "Histogram of tweet counts of unique users"
    tmp_counts = [int(x['user']['statuses_count']) for x in users]
    #
    (hist['user_n_tweets_overall']['data'], hist['user_n_tweets_overall']['bins']) = numpy.histogram(tmp_counts, bins=n_bins)

    if plotGraphs:
        bins = hist['user_n_tweets_overall']['bins'][:-1]
        data = hist['user_n_tweets_overall']['data']
        width = (hist['user_n_tweets_overall']['bins'][1] - hist['user_n_tweets_overall']['bins'][0])/2
        plot.bar(bins, data, width=width, align='center')

        xticklabels = bins

        plot.xticks(bins, xticklabels)
        plot.title(sec_title)
        #plot.show()
        plot.savefig('3.pdf', dpi=600)
    #
    sec_title = "What percentage of them have lower than 5 tweets?"
    n_lower_than_threshold = 0
    for u in users:
        if u['user']['statuses_count'] < 5:
            n_lower_than_threshold += 1

    hist['n_lower_than_threshold'] = n_lower_than_threshold
    print "%s: %0.2f%%" % (sec_title, 100*(float(n_lower_than_threshold)/n_unique_users))

    print hist

    # converting numpy.array's to normal python lists.
    for k in hist.keys():
        if type(hist[k]) == dict:
            for k2 in hist[k].keys():
                if type(hist[k][k2]) == type(numpy.array([])):
                    hist[k][k2] = list(hist[k][k2])

    hist = {'campaign_id': campaign_id,
            'histogram': hist,
            'created_at': now_in_drnj_time()}
    histograms_coll.insert(hist)

    return [hist]
    #####
    #
    # Fetch the profile images of each unique user. Calculate the average color.
    # Form a new image u_1 of one pixel with this color. Then use these u_x to form
    # a final histogram.
    #
    # Treat mentions and retweets as the same and form an edge for each one of them.
    # 1. Plot this graph.
    # 2. Take a basic algorithm and calculate the clusterings in it.
    #

def get_campaign_histograms(campaign_id):
    hists = histograms_coll.find({'campaign_id': campaign_id}).sort([('created_at', -1)])
    return hists


def move_to_history(user_id):
    tweets_coll.update({'tweet.user.id_str': user_id, 'tweet.user.history': False},
                       {'$set': {'tweet.user.history': True}})

def insert_tweet(tweet_obj_array):

    # actual tweet insertion
    tweets_coll.insert(tweet_obj_array)

    for tweet_obj in tweet_obj_array:

        # build the analytics
        freq = {}

        campaign_id = tweet_obj['campaign_id']

        # strip unnecessary fields
        tweet_obj = tweet_obj['tweet']

        freq['campaigns'] = {campaign_id: 1}

    # freq['tokens'] = {'ali': 1, 'veli': 1}

        freq['hashtags'] = {}
        if 'entities' in tweet_obj and 'hashtags' in tweet_obj['entities']:
            for hashtag in tweet_obj['entities']['hashtags']:
                if 'text' in hashtag:
                    item_key = hashtag['text']
                    if item_key in freq['hashtags']:
                        freq['hashtags'][item_key] += 1
                    else:
                        freq['hashtags'][item_key] = 1
                else:
                    # log this missing attribute.
                    pass

        freq['mentions'] = {}
        if 'entities' in tweet_obj and 'user_mentions' in tweet_obj['entities']:
            for mention in tweet_obj['entities']['user_mentions']:
                if 'id_str' in mention:
                    item_key = "|".join([mention['id_str'], mention['screen_name']])
                    if item_key in freq['mentions']:
                        freq['mentions'][item_key] += 1
                    else:
                        freq['mentions'][item_key] = 1
                else:
                    # log this missing attribute.
                    pass

        freq['urls'] = {}
        if 'entities' in tweet_obj and 'urls' in tweet_obj['entities']:
            for url in tweet_obj['entities']['urls']:
                if 'expanded_url' in url:
                    item_key = url['expanded_url']
                    if item_key in freq['urls']:
                        freq['urls'][item_key] += 1
                    else:
                        freq['urls'][item_key] = 1
                else:
                    # log this missing attribute.
                    pass

        if 'created_at' in tweet_obj:
            # turns out that we've already transformed into drnj_time
            t = drnj_time2py_time(tweet_obj['created_at'])
        else:
            t = time.time()

        gm_t = time.gmtime(t)

        today_str = time.strftime('%Y-%m-%d', gm_t)
        hour = time.strftime('%H', gm_t)
        minute = "%04d" % (int(hour)*60 + int(time.strftime('%M', gm_t)))
        # print today_str
        # print hour + ':' + minute

        for key in freq:
            for item in freq[key].keys():
                count = freq[key][item]
                colls[key].update({'campaign_id': campaign_id, 'date': today_str, 'key': item},
                                  {'$inc': {('hour.%s' % hour): count, ('minute.%s' % minute): count, ('day_total'): count},
                                   '$set': {'last_updated_minute': minute}}, upsert=True)