#!/usr/bin/env python
import logging
logging.basicConfig(level=logging.INFO)
import os
import time
import timeit
import usermapper
then = timeit.default_timer()
abc = usermapper.Usermapper(app_token=os.environ.get("SLACK_APP_TOKEN"),
                            bot_token=os.environ.get("SLACK_BOT_TOKEN"),
                            max_workers=50)
elapsed = timeit.default_timer() - then
logging.info("Object creation took %s s." % str(elapsed))
then = timeit.default_timer()
abc.wait_for_initialization(delay=0.1)
elapsed = timeit.default_timer() - then
logging.info("Object initialization took %s s." % str(elapsed))
adam_gh = abc.github_for_slack_user("adam")
wom_slack = abc.slack_for_github_user("womullan")
logging.info("adam [Slack] -> %s [GH]" % adam_gh)
logging.info("womullan [GH] -> %s [Slack]" % wom_slack)
