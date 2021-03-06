#!/usr/bin/env python

#
# Copyright 2012 Onur Gungor <onurgu@boun.edu.tr>
#

import sys, threading, time

import twitter

import math

import requests

import bson.json_util

import logging, logging.handlers

import Queue
import sqlite3
import httplib, urllib2

import re

# local
from drenaj.client.config.config import *

import datetime
import rfc822


ABORTING_WAIT_TOO_LONG_CODE = 1
NOT_AUTHORIZED_ERROR_CODE = -1
PAGE_NOT_FOUND_ERROR_CODE = -2
HTTP_EXCEPTION_CODE = -3
URL_EXCEPTION_CODE = -4
UNKNOWN_EXCEPTION_CODE = -5


class FriendHarvester(threading.Thread):

    def __init__(self, twitter_api, logger, user, requestType):

        # required for threads
        super(FriendHarvester, self).__init__()

        self.user = user
        self.requestType = requestType

        if self.user['id_str']:
            self.use_screenname = False
            self.user_identifier = self.user['id_str']
        else:
            self.use_screenname = True
            self.user_identifier = self.user['screen_name']

        #self.screenname = screenname

        self.drenaj_auth_secrets = KeyStore().drenaj_auth_secrets.copy()
        self.drenaj_store_url= ''

        self.drenaj_store_url = 'http://'+DRENAJ_APP_HOST+':'+str(DRENAJ_APP_PORT[DRENAJ_APP_ENVIRONMENT])+ '/' + requestType +'/list/store'

        self.logger = logger
        self.logger.info("Starting thread "+self.getJobDescription())

        self.api = twitter_api
        self.results_queue = Queue.Queue()

        self.log(self.getJobDescription())

        # self.sleep_duration = sleep_duration_between_calls
        # self.sleep_duration = int(reset_sleep_duration / remaining_rate_limit) + 1

    def log(self, text):
        # self.logfile.write(text+"\n")
        # self.logfile.flush()
        self.logger.info(text)

    def getJobDescription(self):
        return self.user_identifier

    def getRemainingRateLimit(self):
        ## rate_limit_status = self.api.GetRateLimitStatus()
        (ret_code, rate_limit_status) = self.makeApiCall(self.api.GetRateLimitStatus,self.requestType)

        ## if there is an error
        if ret_code != 0:
            return [None, None]
        friend_id_limit = rate_limit_status.get('/'+ self.requestType +'/ids',None)
        reset_time  = friend_id_limit.get('reset', None)
        limit = friend_id_limit.get('remaining', None)

        if reset_time:
            # put the reset time into a datetime object
            reset = datetime.datetime(*rfc822.parsedate(reset_time)[:7])

            # find the difference in time between now and the reset time + 1 hour
            delta = reset + datetime.timedelta(minutes=10) - datetime.datetime.utcnow()

            return [int(delta.seconds), int(limit)]
        else:
            return [5, 1]

    def get_user_identifier(self, user):
        user_identifier = ''
        if 'id' in user:
            user_identifier = str(user['id'])
        elif 'id_str' in user:
            user_identifier = user['id_str']
        else:
            user_identifier = user['screen_name']
        return user_identifier


    def makeApiCall(self, func, *args):
        finished = False
        backoff_duration = 0
        count = 0
        ret_code = 0
        while not finished:
            try:
                if backoff_duration != 0:
                    self.log(self.getJobDescription()+ ": BACKOFF: "+str(backoff_duration)+" "+str(func))
                    time.sleep(backoff_duration)
                if len(args) != 0:
                    ret = func(*args)
                else:
                    ret = func()
                finished = True
            except twitter.TwitterError as e:
                self.log(self.getJobDescription() + ": makeApiCall: " + ": " + str(e.message))
                if e.message == "Sorry, you are not authorized to see this status":
                    return [NOT_AUTHORIZED_ERROR_CODE, None]
                if type(e.message) == type([]):
                    tmp_h = e.message[0]
                    self.log(self.getJobDescription() + ": makeApiCall: ERROR: code: " + str(tmp_h['code']) + " " + str(tmp_h['message']))
                    return [PAGE_NOT_FOUND_ERROR_CODE, None]
                elif e.message.find("Not authorized") == 0:
                    return [NOT_AUTHORIZED_ERROR_CODE, None]
                if backoff_duration == 0:
                    backoff_duration = 2
                else:
                    backoff_duration = backoff_duration * 2
                if backoff_duration > 512:
                    if count == 2:
                        self.log(self.getJobDescription() + ": makeApiCall: ABORTING_WAIT_TOO_LONG")
                        return [ABORTING_WAIT_TOO_LONG_CODE, None]
                    backoff_duration = 512
                    if func.__name__ != 'Api.MaximumHitFrequency' and func.__name__ != 'Api.GetRateLimitStatus':
                        count += 1
            except httplib.HTTPException as e:
                self.log(self.getJobDescription() + ": makeApiCall: " + str(e))
                return [HTTP_EXCEPTION_CODE, None]
            except urllib2.URLError as e:
                self.log(self.getJobDescription() + ": makeApiCall: " + str(e))
                return [URL_EXCEPTION_CODE, None]
            except Exception as e:
                self.log(self.getJobDescription() + ": makeApiCall: " + str(e))
                return [UNKNOWN_EXCEPTION_CODE, None]
        return [ret_code, ret]

    def run(self):
       result = self.fetchFriendsOfUser()
       self.results_queue.put(result)

    def GetFriendsOfUser(self, *args):

        self.log('use_screenname : ' + str(self.use_screenname) + ' - user_identifier : ' + str(self.user_identifier))

        if self.requestType == 'friends':
            if self.use_screenname:
                return self.api.GetFriendIDs(user_id=None,screen_name=self.user_identifier,stringify_ids=True)
            else:
                return self.api.GetFriendIDs(user_id=self.user_identifier,screen_name=None,stringify_ids=True)

        elif self.requestType == 'followers':
            if self.use_screenname:
                return self.api.GetFollowerIDs(user_id=None,screen_name=self.user_identifier,stringify_ids=True)
            else:
                return self.api.GetFollowerIDs(user_id=self.user_identifier,screen_name=None,stringify_ids=True)

    def fetchFriendsOfUser(self):
        all_friends = []
        page_not_found = 0
        finished = False
        n_friends_retrieved = 0


        while not finished:
            ### make an api call
            sleep_duration = self.api.GetSleepTime('/' + self.requestType + '/ids')
            self.log(self.getJobDescription() + ": Sleeping for "+str(sleep_duration)+" seconds to prevent being rate limited")
            time.sleep(sleep_duration)

            self.log(self.getJobDescription() + ": will be retrieved cursor id for this request: ")
            (ret_code, friends) = self.makeApiCall(self.GetFriendsOfUser)
            if friends == None:
               friends = []

            finished = True

            ### write received tweets and determine the max_id
            if len(friends) > 0:
                all_friends = all_friends + friends
                n_friends_retrieved += len(friends)


        if ret_code == PAGE_NOT_FOUND_ERROR_CODE or ret_code == NOT_AUTHORIZED_ERROR_CODE:
            page_not_found = 1

        self.log(self.getJobDescription() + ": Retrieved "+str(n_friends_retrieved)+" "+ self.requestType +" of user.")
        #for i in range(1, len(all_tweets)+1):
        #    tweet = all_tweets[len(all_tweets)-i]
            ##print tweet.AsJsonString()

        self.post_friends(self.process_all_friends(all_friends))
#        return [last_tweet_id, since_tweet_id, n_tweets_retrieved, page_not_found]
        return [n_friends_retrieved, page_not_found]

    def post_friends(self, tmp):
        if not tmp:
            return

        n_friends = len(tmp)

        self._post_friends(tmp)

        # I had to comment this out because this was wrong given the current
        # code on /friends|followers/list/store (it was deleting all the current edges into/out
        # from the user.
        # batch_size = 100
        #
        # while len(tmp) > 0:
        #     self.log("%d friends/followers to post." % len(tmp))
        #     batch = []
        #     if len(tmp) >= batch_size:
        #         batch = tmp[0:batch_size]
        #         tmp = tmp[batch_size:]
        #     else:
        #         batch = tmp
        #         tmp = []
        #     self._post_friends(batch)

    def _post_friends(self, batch):
        params = dict()
        params.update({'user_objects': bson.json_util.dumps(batch)})

        if self.user['id_str']:
            params.update({'id_str': self.user['id_str']})
        else:
            params.update({'screen_name': self.user['screen_name']})

        self.post_to_gateway(params, self.drenaj_store_url)

    def process_all_friends(self, all_friends):
        tmp = []
        for friend_id_str in all_friends:
            friend_json = {}
            friend_json['id_str'] = friend_id_str
            tmp.append(friend_json)
        return tmp


    # TODO: Is it possible to make this call concurrent?
    def post_to_gateway(self, params, url):

        ##xxx We have converted to JSON in this case.
        ## params.update({'tweet_data': tmp})
        params.update(self.drenaj_auth_secrets)

        # print params
        # TODO: here, error no 111 connection refused exception must be try-catched.
        stop_trying = False
        exp_backoff_duration = 1
        response = None
        while not stop_trying:
            try:
                response = requests.post(url,
                                        data=params)
                stop_trying = True
            except requests.exceptions.ConnectionError, e:
                if exp_backoff_duration > 2**2:
                    stop_trying = True
                    # TODO: log this issue at this point.
                else:
                    time.sleep(exp_backoff_duration)
                    exp_backoff_duration *= 2

        if response:
            print "Posted Friend/Follower Info. RESPONSE CODE: %s LENGTH: %s" %(response.status_code, len(response.content))



import celery
from celery.utils.log import get_task_logger

from celery.signals import worker_shutdown

class FriendFollowerHarvesterTask(celery.Task):
    name = 'crawl_friends_or_followers'
    max_retries = None

    def __init__(self):

        # LOGGING SETUP START
        #self.logger = logging.getLogger('main_logger')
        self.logger = get_task_logger(__name__)
        #self.logger.setLevel(logging.DEBUG)
        #handler = logging.handlers.RotatingFileHandler(filename="./messages.log", maxBytes=10**7, backupCount=10)
        #handler.setFormatter(logging.Formatter('%(asctime)s:: %(message)s', '%Y-%m-%d %I:%M:%S %p'))

        #self.logger.addHandler(handler)

        self.logger.info("Logging set up.")
        # LOGGING SETUP END

        self.rate_limit = 350
        self.estimated_max_calls_per_screenname = 17
        self.tolerance_duration = 5

        print "END INIT FriendFollowerHarvesterTask"

        # n_running_jobs = 0

        ## INITIALIZATION END

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        print "ON_FAILURE"
        self.on_shutdown()

    def on_success(self, retval, task_id, args, kwargs):
        print "ON_SUCCESS"
        self.on_shutdown()

    def on_shutdown(self):
        print "ON_SHUTDOWN"
        keystore = KeyStore()
        keystore.release_access_tokens(self.access_tokens)

    def get_user_identifier(self, user):
        user_identifier = ''
        if user['id_str']:
            user_identifier = user['id_str']
        else:
            user_identifier = user['screen_name']
        return user_identifier

    # By default, we use user_id_str's.
    def run(self, user_info_table, use_screenname=False):
        worker_shutdown.connect(self.on_shutdown)

        print type(user_info_table)
        print user_info_table

        keystore = KeyStore()
        #self.keystore.load_access_tokens_from_file()
        self.access_tokens = keystore.acquire_access_tokens()
        print "DENEME"

        # If there is no available access_tokens
        if not self.access_tokens:
           self.logger.error("No access tokens. Sorry. Sending a message to retry 3 mins later."
                             "Hopefully someone else will pick it up, if it's not me.")
           raise self.retry(countdown=3*60)

        self.available_twitter_api_array = []

        i = 1
        for key_and_secret in self.access_tokens:
            api = twitter.Api(keystore.app_consumer_key, keystore.app_consumer_secret, key_and_secret[0], key_and_secret[1], cache=None)
            self.available_twitter_api_array.append(["(key %s)" % i, api])
            i += 1

        self.jobs = []

        self.use_screenname = use_screenname

        self.user_info_table = user_info_table
        self.n_user_identifiers = len(self.user_info_table)

        finished = False
        while not finished:
            while len(self.user_info_table) > 0:
                # Assign stale API connections to the next job items.
                # If there is a stale API connection, continue
                if len(self.available_twitter_api_array) > 0:

                    (user, page_not_found) = self.user_info_table.pop()
                    user_identifier = self.get_user_identifier(user)

                    # (since_tweet_id, page_not_found, update_required) = get_userinfo(self.db_cursor, user_identifier)

                    if page_not_found == 1:
                        self.logger.info("Skipping " + user_identifier + " (we got page not found error before)")
                    # removed this because this decision is taken at drenaj_api
                    # elif not update_required:
                    #    self.logger.info("Skipping " + user_identifier + " (not expired yet)")
                    else:
                        [token_owner_name, api] = self.available_twitter_api_array.pop()
                        t = FriendHarvester(api, self.logger, user,'friends')
                        task_start_time = time.time()
                        t.start()

                        self.logger.info("PROGRESS: " + str(len(self.user_info_table)) + "/"+str(self.n_user_identifiers))
                        self.logger.info("Thread Friend Harvester " + token_owner_name + " => "+user_identifier+" starting..")
                        self.jobs.append([t, user, task_start_time, api, token_owner_name])

                        t2 = FriendHarvester(api, self.logger, user,'followers')
                        task_start_time2 = time.time()
                        t2.start()

                        self.logger.info("Thread Follower Harvester " + token_owner_name + " => "+user_identifier+" starting..")
                        self.jobs.append([t2, user, task_start_time2, api, token_owner_name])


                else:
                    # No stale API connections found, break out of this loop.
                    break

            if len(self.jobs) == 0:
                finished = True
            tmp_jobs = []
            while len(self.jobs) > 0:
                job = self.jobs.pop()
                [t, user, task_start_time, api, token_owner_name] = job
                user_identifier = self.get_user_identifier(user)
                t.join(0.001)
                if not t.isAlive():
                    time_elapsed = int(time.time()-task_start_time)
                    self.logger.info("Stopping thread "+user_identifier+" - (duration: "+str(time_elapsed)+" secs) - "+token_owner_name)
                    # update_userinfo(self.db_cursor, user_identifier, update_since_tweet_id, *result)
                    self.available_twitter_api_array.append([token_owner_name, api])
                else:
                    tmp_jobs.append(job)
            self.jobs = tmp_jobs