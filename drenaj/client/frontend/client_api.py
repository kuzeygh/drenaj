'''
Client side API which will be used at our clients' machines

'''

# Change History :
# Date                                          Prog    Note
# Thu Oct 10 10:09:20 2013                      ATC     Created, Python 2.7.3

# ATC = Ali Taylan Cemgil,
# Department of Computer Engineering, Bogazici University
# e-mail :  taylan.cemgil@boun.edu.tr

import tornado.ioloop
import tornado.web
from tornado.web import MissingArgumentError

from tornado.web import HTTPError

#from tornado.escape import json_decode
import requests
import bson.json_util

from drenaj.client.config.config import *

from drenaj.client.workers.streamcatcher import StreamCatcher
from drenaj.client.workers.twitter_api_getfollowers import drnj_graph_crawler


threads = []

## import signal, sys
## def stop_all_threads(signal, frame):
##     print 'Stopping all threads'
##     for t in threads:
##         t.terminate()
##     sys.exit(0)
##
## signal.signal(signal.SIGINT, stop_all_threads)

app_root_url = 'http://' + DRENAJ_APP_HOST + ':' + str(DRENAJ_APP_PORT[DRENAJ_APP_ENVIRONMENT])
vis_root_url = 'http://' + DRENAJ_VIS_HOST + ':' + str(DRENAJ_VIS_PORT[DRENAJ_VIS_ENVIRONMENT])

keystore = KeyStore()

class TaskHandler(tornado.web.RequestHandler):
    def get(self, *args):
        self.post(*args)
        #self.write("not implemented yet")

    def post(self, *args):
        """

        """

        env = self.application.settings['env']

        task_type = args[0]

        print "TaskHandler: {}".format(task_type)

        try:
            if task_type == 'friendfollower':

                user_id = self.get_argument('user_id')
                campaign_id = self.get_argument('campaign_id')
                local_or_remote = self.get_argument('local_or_remote', 'local')

                task_definition = bson.json_util.dumps({'task_type': task_type,
                                   'metadata': {
                                      'user': {
                                          'id_str': user_id,
                                          },
                                      }
                                  })
                print task_definition

                #if local_or_remote == 'local':
                #    res = drnj_graph_crawler(friends_or_followers, int(user_id))
                #else:
                #    # TODO: implement remote work submission
                #    pass

                if local_or_remote == 'local':
                    post_data = {'task_definition': task_definition,
                                 'queue': DRENAJ_LOCAL_QUEUE}
                else:
                    post_data = {'task_definition': task_definition,
                                 'queue': 'timelines'}

                res = requests.post(app_root_url + '/tasks/' + task_type, data=post_data)
                task_submit_result = bson.json_util.loads(res.content)
                print task_submit_result

                template = env.get_template('tasks/notification.html')
                result = template.render(task_submit_result=task_submit_result, href=vis_root_url, campaign_id=campaign_id)

                self.write(result)

                #template = env.get_template('profiles/crawl_graph_notification.html')
                #task_submit_result = template.render(user_id=user_id, fof=friends_or_followers, res=res, href=vis_root_url)

                #self.write(task_submit_result)
            elif task_type == 'timeline':
                from drenaj.client.celery_app.client_endpoint import app_object
                user_id = self.get_argument('user_id', '')
                campaign_id = self.get_argument('campaign_id')
                screen_name = self.get_argument('screen_name', '')
                #since_tweet_id = self.get_argument('since_tweet_id', '-1')
                local_or_remote = self.get_argument('local_or_remote', 'local')

                task_definition = bson.json_util.dumps({'task_type': task_type,
                                   'metadata': {
                                      'user': {
                                          'id_str': user_id,
                                          'screen_name': screen_name
                                          }
                                      }
                                  })
                print task_definition

                if local_or_remote == 'local':
                    post_data = {'task_definition': task_definition,
                                 'queue': DRENAJ_LOCAL_QUEUE}
                else:
                    post_data = {'task_definition': task_definition,
                                 'queue': 'timelines'}

                res = requests.post(app_root_url + '/tasks/' + task_type, data=post_data)
                task_submit_result = bson.json_util.loads(res.content)
                print task_submit_result

                template = env.get_template('tasks/notification.html')
                result = template.render(task_submit_result=task_submit_result, href=vis_root_url, campaign_id=campaign_id)

                self.write(result)
            elif task_type == 'userinfo':
                from drenaj.client.celery_app.client_endpoint import app_object
                user_id = self.get_argument('user_id', '')
                campaign_id = self.get_argument('campaign_id') # unnecessary for the task but it used for going back to the right page.
                #since_tweet_id = self.get_argument('since_tweet_id', '-1')
                local_or_remote = self.get_argument('local_or_remote', 'local')

                task_definition = bson.json_util.dumps({'task_type': task_type,
                                   'metadata': {
                                      'user': {
                                          'id_str': user_id,
                                          }
                                      }
                                  })
                print task_definition

                if local_or_remote == 'local':
                    post_data = {'task_definition': task_definition,
                                 'queue': DRENAJ_LOCAL_QUEUE}
                else:
                    post_data = {'task_definition': task_definition,
                                 'queue': 'userinfo'}

                res = requests.post(app_root_url + '/tasks/' + task_type, data=post_data)
                task_submit_result = bson.json_util.loads(res.content)
                print task_submit_result

                template = env.get_template('tasks/notification.html')
                result = template.render(task_submit_result=task_submit_result, href=vis_root_url, campaign_id=campaign_id)

                self.write(result)
            else:
                pass
        except MissingArgumentError as e:
            # TODO: implement logging.
            raise HTTPError(500, 'You didn''t supply %s as an argument' % e.arg_name)


#  (r"/(friends|followers)/(crawl|view)", ClientFriendFollowerHandler),
class ClientFriendFollowerHandler(tornado.web.RequestHandler):
    def get(self, *args):
        self.post(*args)
        #self.write("not implemented yet")

    def post(self, *args):
        """

        """

        env = self.application.settings['env']

        (friends_or_followers, crawl_or_view) = args

        print "ClientFriendFollowerHandler: {} {}".format(friends_or_followers, crawl_or_view)

        if crawl_or_view=='crawl':
            user_id = self.get_argument('user_id', None)

            res = drnj_graph_crawler(friends_or_followers, int(user_id))

            template = env.get_template('profiles/crawl_graph_notification.html')
            result = template.render(user_id=user_id, fof=friends_or_followers, res=res, href=vis_root_url)

            self.write(result)
        else:
            pass

#    (r"/user/(crawl|view)", visSingleProfileHandler),
class visSingleProfileHandler(tornado.web.RequestHandler):
    def get(self, *args):
        self.post(*args)
        #self.write("not implemented yet")

    def post(self, *args):
        """

        """

        env = self.application.settings['env']

        (crawl_or_view) = args

        print "visSingleProfileHandler: {} ".format(crawl_or_view)

        user_id = self.get_argument('user_id', None)
        post_data = {"user_id": user_id}
        post_response = requests.post(url=app_root_url + '/profiles/view', data=post_data)

        #dat = json_decode(post_response.content)
        dat = bson.json_util.loads(post_response.content)
        print dat

        template = env.get_template('profiles/history_view.html')
        result = template.render(profiles=dat)

        self.write(result)

#    (r"/campaigns/view/watched_users", CampaignsWatchedUsersHandler),
class CampaignsWatchedUsersHandler(tornado.web.RequestHandler):
    def get(self, *args):
        self.post(*args)
        #self.write("not implemented yet")

    def post(self, *args):
        """

        """

        env = self.application.settings['env']

        (crawl_or_view) = args

        print "CampaignsWatchedUsersHandler: {} ".format(crawl_or_view)

        campaign_id = self.get_argument('campaign_id', 'default')
        skip = self.get_argument('skip', 0)
        limit = self.get_argument('limit', 100)

        post_data = {"campaign_id": campaign_id,
                     'skip': skip,
                     'limit': limit}

        response = requests.post(url=app_root_url + '/campaigns/view/watched_users',
                                 data=post_data)

        response_json = bson.json_util.loads(response.content)
        print response_json

        watched_users = response_json['watched_users']

        # response = requests.post(url=app_root_url + '/profiles/view/user',
        #                          data={'user_id_list': ",".join(watched_users_id_strs)})
        #
        # response_json = bson.json_util.loads(response.content)
        # print response_json
        #
        # input_array = []
        # i = 0
        # for user in response_json:
        #     since_tweet_id = watched_users_since_tweet_ids[i]
        #     input_array.append([user, since_tweet_id])
        #     i += 1

        template = env.get_template('campaigns/view/watched_users.html')
        result = template.render(profiles=watched_users, href=vis_root_url, campaign_id=campaign_id, skip=skip, limit=limit)

        self.write(result)

#    (r"/campaigns/(list|new|create_thread|kill_thread)", visCampaignsHandler),
class visCampaignsHandler(tornado.web.RequestHandler):
    def get(self, *args):
        self.post(*args)
        #self.write("not implemented yet")

    def post(self, *args):
        """

        """

        env = self.application.settings['env']

        (command) = args[0]

        print "visCampaignsHandler: {} ".format(command)
        drenaj_auth_secrets = keystore.drenaj_auth_secrets.copy()

        if command == "new":
            campaign_id = self.get_argument('campaign_id')
            campaign_type = self.get_argument('campaign_type')
            description = self.get_argument('description')
            query_terms = self.get_argument('query_terms')
            user_id_strs_to_follow = self.get_argument('user_id_strs_to_follow')
            user_screen_names_to_follow = self.get_argument('user_screen_names_to_follow')
            post_data = {"campaign_id": campaign_id,
                         "campaign_type": campaign_type,
                         "description": description,
                         "query_terms": query_terms,
                         "user_id_strs_to_follow": user_id_strs_to_follow,
                         "user_screen_names_to_follow": user_screen_names_to_follow}
            post_data.update(drenaj_auth_secrets)
            post_response = requests.post(url=app_root_url + '/campaigns/new', data=post_data)
            print post_response.content
            dat = bson.json_util.loads(post_response.content)

            #self.createThread(campaign_id, query_terms)

            template = env.get_template('campaigns/new.html')
            result = template.render(result=dat)
        elif command == "list":
            print "list"
            post_response = requests.post(url=app_root_url + '/campaigns/list', data=drenaj_auth_secrets)
            print "ok"
            dat = bson.json_util.loads(post_response.content)

            template = env.get_template('campaigns/list.html')
            result = template.render(campaigns=dat, threads=threads)
        elif command == "create_thread":
            campaign_id = self.get_argument('campaign_id')
            query_terms = self.get_argument('query_terms')

            self.createThread(campaign_id, query_terms)

            template = env.get_template('campaigns/new.html')
            result = template.render(result={'status': 'success'})
        elif command == "kill_thread":
            campaign_id = self.get_argument('campaign_id')

            self.killThread(campaign_id)

            template = env.get_template('campaigns/new.html')
            result = template.render(result={'status': 'success'})

        self.write(result)

    def createThread(self, campaign_id, query_terms):
        t = StreamCatcher(
                campaign_id=campaign_id,
                postdata={"track": query_terms})
        t.start()
        threads.append([t, campaign_id, query_terms])

    def killThread(self, campaign_id):
        i = 0
        while True:
            if i == len(threads):
                break
            else:
                thread = threads[i]
                if thread[1] == campaign_id:
                    threads.pop(i)
                    thread[0].terminate()
                else:
                    i = i + 1