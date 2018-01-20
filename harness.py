#!/usr/bin/env python
import logging
logging.basicConfig(level=logging.INFO)
import os
import usermapper
abc = usermapper.Usermapper(app_token=os.environ.get("SLACK_APP_TOKEN"),
                            bot_token=os.environ.get("SLACK_BOT_TOKEN"),
                            max_workers=50)
adam_gh = abc.github_for_slack_user("adam")
wom_slack = abc.slack_for_github_user("womullan")
print("adam [Slack] -> %s [GH]" % adam_gh)
print("womullan [GH] -> %s [Slack]" % wom_slack)
