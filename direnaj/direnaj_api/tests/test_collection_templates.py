import pytest

import bson.json_util

from direnaj.direnaj_collection_templates import *

print __package__

def test_collection_templates():

    obj = bson.json_util.loads(
    '''
        {\"retrieved_by\": \"direnaj\",
\"tweet\": {\"contributors\": null,
\"truncated\": false,
\"text\": \"RT @kiyametprojesi: 22:58, Cihangir, \u015fu an. Geri \u00e7ekilmiyoruz! Eve d\u00f6nm\u00fcyoruz! #AhmetAtakan http://t.co/x6wPBYOMhP\",
\"in_reply_to_status_id\": null,
\"id\": 377522017911599104,
\"favorite_count\": 0,
\"source\": \"web\",
\"retweeted\": false,
\"coordinates\": null,
\"entities\": {\"symbols\": [],
\"user_mentions\": [{\"indices\": [3,
18],
\"screen_name\": \"kiyametprojesi\",
\"id\": 501178919,
\"name\": \"Bar\u0131\u015f\",
\"id_str\": \"501178919\"}],
\"hashtags\": [{\"indices\": [79,
91],
\"text\": \"AhmetAtakan\"}],
\"urls\": [],
\"media\": [{\"source_status_id_str\": \"377521829419962368\",
\"expanded_url\": \"http://twitter.com/kiyametprojesi/status/377521829419962368/photo/1\",
\"display_url\": \"pic.twitter.com/x6wPBYOMhP\",
\"url\": \"http://t.co/x6wPBYOMhP\",
\"media_url_https\": \"https://pbs.twimg.com/media/BT06GoRIAAALYvr.jpg\",
\"source_status_id\": 377521829419962368,
\"id_str\": \"377521829331861504\",
\"sizes\": {\"small\": {\"h\": 453,
\"resize\": \"fit\",
\"w\": 340},
\"large\": {\"h\": 1024,
\"resize\": \"fit\",
\"w\": 768},
\"medium\": {\"h\": 800,
\"resize\": \"fit\",
\"w\": 600},
\"thumb\": {\"h\": 150,
\"resize\": \"crop\",
\"w\": 150}},
\"indices\": [92,
114],
\"type\": \"photo\",
\"id\": 377521829331861504,
\"media_url\": \"http://pbs.twimg.com/media/BT06GoRIAAALYvr.jpg\"}]},
\"in_reply_to_screen_name\": null,
\"id_str\": \"377522017911599104\",
\"retweet_count\": 0,
\"in_reply_to_user_id\": null,
\"favorited\": false,
\"retweeted_status\": {\"contributors\": null,
\"truncated\": false,
\"text\": \"22:58, Cihangir, \u015fu an. Geri \u00e7ekilmiyoruz! Eve d\u00f6nm\u00fcyoruz! #AhmetAtakan http://t.co/x6wPBYOMhP\",
\"in_reply_to_status_id\": null,
\"id\": 377521829419962368,
\"favorite_count\": 0,
\"source\": \"<a href=\\"http://twitter.com/download/iphone\\" rel=\\"nofollow\\">Twitter for iPhone</a>\",
\"retweeted\": false,
\"coordinates\": null,
\"entities\": {\"symbols\": [],
\"user_mentions\": [],
\"hashtags\": [{\"indices\": [59,
71],
\"text\": \"AhmetAtakan\"}],
\"urls\": [],
\"media\": [{\"expanded_url\": \"http://twitter.com/kiyametprojesi/status/377521829419962368/photo/1\",
\"sizes\": {\"small\": {\"h\": 453,
\"resize\": \"fit\",
\"w\": 340},
\"large\": {\"h\": 1024,
\"resize\": \"fit\",
\"w\": 768},
\"medium\": {\"h\": 800,
\"resize\": \"fit\",
\"w\": 600},
\"thumb\": {\"h\": 150,
\"resize\": \"crop\",
\"w\": 150}},
\"url\": \"http://t.co/x6wPBYOMhP\",
\"media_url_https\": \"https://pbs.twimg.com/media/BT06GoRIAAALYvr.jpg\",
\"id_str\": \"377521829331861504\",
\"indices\": [72, 94],
\"media_url\": \"http://pbs.twimg.com/media/BT06GoRIAAALYvr.jpg\",
\"type\": \"photo\",
\"id\": 377521829331861504,
\"display_url\": \"pic.twitter.com/x6wPBYOMhP\"}]},
\"in_reply_to_screen_name\": null,
\"id_str\": \"377521829419962368\",
\"retweet_count\": 4,
\"in_reply_to_user_id\": null,
\"favorited\": false,
\"user\": {\"follow_request_sent\": null,
\"profile_use_background_image\": true,
\"geo_enabled\": false,
\"verified\": false,
\"profile_image_url_https\": \"https://si0.twimg.com/profile_images/378800000144578061/1bb74ef86023bab523225383567bf81c_normal.jpeg\",
\"profile_sidebar_fill_color\": \"DDEEF6\",
\"id\": 501178919,
\"profile_text_color\": \"333333\",
\"followers_count\": 1580,
\"profile_sidebar_border_color\": \"C0DEED\",
\"location\": \"Alanya, Dublin, \u0130stanbul\",
\"default_profile_image\": false,
\"id_str\": \"501178919\",
\"utc_offset\": 10800,
\"statuses_count\": 3960,
\"description\": \"S\u00fct kokarak geldim, le\u015f kokarak gidece\u011fim.\",
\"friends_count\": 416,
\"profile_link_color\": \"B31E0B\",
\"profile_image_url\": \"http://a0.twimg.com/profile_images/378800000144578061/1bb74ef86023bab523225383567bf81c_normal.jpeg\",
\"notifications\": null,
\"profile_background_image_url_https\": \"https://si0.twimg.com/profile_background_images/432935757/Ads_z.png\",
\"profile_background_color\": \"C1EBCF\",
\"profile_banner_url\": \"https://pbs.twimg.com/profile_banners/501178919/1360206313\",
\"profile_background_image_url\": \"http://a0.twimg.com/profile_background_images/432935757/Ads_z.png\",
\"name\": \"Bar\u0131\u015f\",
\"lang\": \"tr\",
\"following\": null,
\"profile_background_tile\": true,
\"favourites_count\": 1163,
\"screen_name\": \"kiyametprojesi\",
\"url\": null,
\"created_at\": \"Thu Feb 23 21:47:59 +0000 2012\",
\"contributors_enabled\": false,
\"time_zone\": \"Istanbul\",
\"protected\": false,
\"default_profile\": false,
\"is_translator\": false,
\"listed_count\": 7},
\"geo\": null,
\"in_reply_to_user_id_str\": null,
\"possibly_sensitive\": false,
\"lang\": \"tr\",
\"created_at\": \"Tue Sep 10 19:59:52 +0000 2013\",
\"in_reply_to_status_id_str\": null,
\"place\": null},
\"user\": {\"follow_request_sent\": null,
\"profile_use_background_image\": true,
\"geo_enabled\": false,
\"verified\": false,
\"profile_image_url_https\": \"https://si0.twimg.com/profile_images/378800000386220661/e72b335ec4dd10ec49d9a89d7cdd4357_normal.jpeg\",
\"profile_sidebar_fill_color\": \"A0C5C7\",
\"id\": 96146503,
\"profile_text_color\": \"333333\",
\"followers_count\": 8628,
\"profile_sidebar_border_color\": \"FFFFFF\",
\"location\": \"Athena de\u011fil Ares Olan\u0131 !\",
\"default_profile_image\": false,
\"id_str\": \"96146503\",
\"utc_offset\": 10800,
\"statuses_count\": 36666,
\"description\": \"T.C. Vatan\u0131n b\u00fct\u00fcnl\u00fc\u011f\u00fc ve milletin istikl\u00e2li tehlikededir. Expert Pharmacist , MBA , Yacht Master , Scuba instructor from Marmaris / Izmir S m y r n a\",
\"friends_count\": 1690,
\"profile_link_color\": \"FF3300\",
\"profile_image_url\": \"http://a0.twimg.com/profile_images/378800000386220661/e72b335ec4dd10ec49d9a89d7cdd4357_normal.jpeg\",
\"notifications\": null,
\"profile_background_image_url_https\": \"https://si0.twimg.com/profile_background_images/378800000006471184/e239fde5824c94aca95b7d8eb38db5ce.jpeg\",
\"profile_background_color\": \"709397\",
\"profile_banner_url\": \"https://pbs.twimg.com/profile_banners/96146503/1372464938\",
\"profile_background_image_url\": \"http://a0.twimg.com/profile_background_images/378800000006471184/e239fde5824c94aca95b7d8eb38db5ce.jpeg\",
\"name\": \"Son Y\u00f6r\u00fck \u00c7ad\u0131r\u0131 !\",
\"lang\": \"tr\",
\"following\": null,
\"profile_background_tile\": false,
\"favourites_count\": 184,
\"screen_name\": \"farmares\",
\"url\": \"http://www.twitter.com/farmares\",
\"created_at\": \"Fri Dec 11 15:25:57 +0000 2009\",
\"contributors_enabled\": false,
\"time_zone\": \"Athens\",
\"protected\": false,
\"default_profile\": false,
\"is_translator\": false,
\"listed_count\": 30},
\"geo\": null,
\"in_reply_to_user_id_str\": null,
\"possibly_sensitive\": false,
\"lang\": \"tr\",
\"created_at\": \"Tue Sep 10 20:00:37 +0000 2013\",
\"filter_level\": \"medium\",
\"in_reply_to_status_id_str\": null,
\"place\": null},
\"campaign_id\": \"ahmetatakan\",
\"record_retrieved_at\": 735487.8339717217,
\"direnaj_service_version\": 0.2}
'''
)

    val_obj = validate_document(new_tweet_template(), obj, fail=False)

    import code
    code.interact(local=locals())

    assert True == True


if __name__ == "__main__":
    test_collection_templates()