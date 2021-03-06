import logging

import bson.json_util
import pymongo
import tornado.ioloop
import tornado.web
from jinja2 import Environment, FileSystemLoader
from tornado import gen
from tornado.web import HTTPError
from tornado.web import MissingArgumentError

import utils.drnj_time as drnj_time
from drenaj_api.celery_app.server_endpoint import app_object
from drenaj_api.utils.drenaj_collection_templates import *
from drenaj_api.utils.drenajneo4jmanager import update_task_state_in_watchlist

logger = logging.getLogger("drenaj_api")

def extract_arguments(tweets):
    campaign_id = None
    user_objects = []
    if tweets:
        campaign_id = tweets[0]['campaign_id']

        for tweet in tweets:
            user_objects.append(tweet['tweet']['user'])
    return [campaign_id, user_objects]

class StatusesHandler(tornado.web.RequestHandler):

    ## def datetime_hook(self, dct):
    ##     # TODO: this only checks for the first level 'created_at'
    ##     # We should think about whether making this recursive.
    ##     if 'created_at' in dct:
    ##         time_struct = time.strptime(dct['created_at'], "%a %b %d %H:%M:%S +0000 %Y") #Tue Apr 26 08:57:55 +0000 2011
    ##         dct['created_at'] = datetime.datetime.fromtimestamp(time.mktime(time_struct))
    ##         return bson.json_util.object_hook(dct)
    ##     return bson.json_util.object_hook(dct)


    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, DELETE, PUT, OPTIONS")
        self.set_header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept')

    def options(self, *args):
        self.post(*args)

    def get(self, *args):
        self.post(*args)
        #self.write("not implemented yet")

    def produce_dbpedia_spotlight_result(self, text):
        import requests
        response = requests.post("http://spotlight.sztaki.hu:2222/rest/annotate",
                      {'text': text,
                       'confidence': 0.5,
                       'support': 20})
        return response.content

    #@drenaj_simple_auth
    @tornado.web.asynchronous
    @gen.coroutine
    def post(self, *args, **keywords):
        """
        `view`
            - params:
                - user_id: user_id of the twitter user that we want to
                retrieve all tweets.
        `store`
            - params:
                - tweet_data: array of tweets in json format.
        `retweets`
            - params:
                - tweet_id: `id` of the tweet that we want to
                retrieve all retweets.
        `filter`
            - not implemented yet.
        """

        if len(args) > 1:
            (action) = args
        else:
            action = args[0]

        print action

        verbose_response = self.get_argument('verbose', '')

        if (action == 'view'):
            try:
                # TODO: we need to get here again.
                user_id = self.get_argument('user_id')
                # if no user_id is supplied.
                if user_id == '':
                    tmp = []
                else:

                    tweets_coll = self.application.db.motor_column.tweets
                    # running the query
                    cursor = tweets_coll.find({
                        'tweet.user.id_str': str(user_id),
                    })

                    tmp = [x for x in (yield cursor.to_list(length=100))]

                self.write(bson.json_util.dumps({'results': tmp}))
                self.add_header('Content-Type', 'application/json')
            except MissingArgumentError as e:
                # TODO: implement logging.
                raise HTTPError(500, 'You didn''t supply %s as an argument' % e.arg_name)
        elif (action == 'store'):
            try:
                tweet_data = self.get_argument('tweet_data')
                campaign_id = self.get_argument('campaign_id', 'default')
                watchlist_related = self.get_argument('watchlist_related', '')
                if tweet_data:
                    #tweet_array = bson.json_util.loads(tweet_data, object_hook=self.datetime_hook)
                    tweet_array = bson.json_util.loads(tweet_data)
                    tmp_tweets = []
                    # TODO: Sanity check the data!
                    # For example, treat 'entities', 'user' specially.
                    DB_TEST_VERSION = 0.2
                    for tweet_obj in tweet_array:
                        tweet_obj['user']['history'] = False
                        tmp_tweets.append(validate_document(new_tweet_template(), {
                            "tweet": tweet_obj,
                            # TODO: Replace this DB_TEST_VERSION with source code
                            # version later
                            "drenaj_service_version": DB_TEST_VERSION,
                            # TODO: "retrieved_by": keywords['drnjID'],
                            "retrieved_by": "drenaj",
                            "campaign_id": campaign_id,
                            "record_retrieved_at": drnj_time.now_in_drnj_time(),
                        }, fail=False))
                        ### TODO: add these users later.
                        ### tmp_users.append(validate_document(new_user_template(), tweet_obj['user']))
                    if tmp_tweets:
                        self.application.db.insert_tweet(tmp_tweets)
                        # WARN: This functionality is not available for now.
                        # campaign_id, user_objects = extract_arguments(tmp_tweets)
                        # res = app_object.send_task('init_user_to_graph_offline',
                        #                    [[ campaign_id, bson.json_util.dumps(user_objects) ]],
                        #                    queue="offline_jobs")
                        # logger.info(str(res))
                        if watchlist_related:
                            print watchlist_related
                            watchlist_related = bson.json_util.loads(watchlist_related)
                            print watchlist_related
                            #self.application.db.update_watchlist(**watchlist_related)
                            update_task_state_in_watchlist(**watchlist_related)


                    else:
                        raise HTTPError(500, 'You tried to insert no tweets?!')
#                    tweets_coll.insert(tmp_tweets)
                else:
                    tmp = []

                if verbose_response:
                    self.write(bson.json_util.dumps({'results': tmp}))
                else:
                    self.write(bson.json_util.dumps({'results': 'ok'}))
                self.add_header('Content-Type', 'application/json')
                self.finish()
            except MissingArgumentError as e:
                # TODO: implement logging.
                raise HTTPError(500, 'You didn''t supply %s as an argument' % e.arg_name)
        elif (action == 'retweets'):
            try:
                tweet_id = self.get_argument('tweet_id')
                self.write('not implemented yet')
            except MissingArgumentError as e:
                # TODO: implement logging.
                raise HTTPError(500, 'You didn''t supply %s as an argument' % e.arg_name)
        elif (action == 'filter'):
            try:
                campaign_id = self.get_argument('campaign_id')
                skip = self.get_argument('skip', 0)
                limit = self.get_argument('limit', 100)
                res_format = self.get_argument('format', 'json')
                since_datetime = self.get_argument('since_datetime', -1)
                until_datetime = self.get_argument('until_datetime', -1)
                sort_by_datetime = self.get_argument('sort_by_datetime', 0)
                produce_dbpedia_spotlight_result = self.get_argument('dbpedia_spotlight_result', 0)

                tweets_coll = self.application.db.motor_column.tweets

                query_string = {'campaign_id' : '%s' % campaign_id}
                if since_datetime != -1:
                    if 'tweet.created_at' not in query_string:
                        query_string['tweet.created_at'] = {}
                    query_string['tweet.created_at']['$gte'] = float(since_datetime)
                if until_datetime != -1:
                    if 'tweet.created_at' not in query_string:
                        query_string['tweet.created_at'] = {}
                    query_string['tweet.created_at']['$lt'] = float(until_datetime)
                sort_string = []
                if sort_by_datetime != 0:
                    sort_string = [('tweet.created_at', pymongo.ASCENDING)] # ascending
                print "STARTED " + str(query_string)
                cursor = tweets_coll.find(query_string)
                if sort_string:
                    cursor = cursor.sort(sort_string)
                cursor = cursor.skip(int(skip)).limit(int(limit))
                           # TODO: removing because of complaint:
                           # TypeError: if no direction is specified, key_or_list must be an instance of list
                           # .sort({"$natural" : 1})\
                tmp = []
                for x in (yield cursor.to_list(length=100)):
                    if int(produce_dbpedia_spotlight_result) == 1:
                        x['tweet']['dbpedia_spotlight_result'] = self.produce_dbpedia_spotlight_result(x['tweet']['text'])
                    tmp.append(x)
                # tmp = [x for x in (yield cursor.to_list(length=100))]
                print "ENDED " + str(query_string)
                DB_TEST_VERSION = 0.2
                if res_format == 'json':
                    self.write(bson.json_util.dumps(
                            {'results': tmp,
                            # TODO: Replace this DB_TEST_VERSION with source code
                            # version later
                            "drenaj_service_version": DB_TEST_VERSION,
                            # TODO: "requested_by": keywords['drnjID'],
                            "requested_by": "drenaj",
                            "campaign_id": campaign_id,
                            "served_at": drnj_time.now_in_drnj_time(),
                             'skip': int(skip),
                             'limit': int(limit)}))
                    self.add_header('Content-Type', 'application/json')
                elif res_format == 'html':
                    env = Environment(loader=FileSystemLoader('templates'))

                    template = env.get_template('statuses/filter.html')
                    result = template.render(statuses=[x['tweet'] for x in tmp])
                    self.write(result)

                self.finish()

            except MissingArgumentError as e:
                # TODO: implement logging.
                raise HTTPError(500, 'You didn''t supply %s as an argument' % e.arg_name)
            # db.tweets.find({'campaign_id' : 'syria'}).sort({$natural : 1}).skip(10).limit(14)
        else:
            # Tornado will make sure that this point will not be reached, if
            # it's regexp based router works correctly
            raise HTTPError(404, 'No such method')
