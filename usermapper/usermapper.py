#!/usr/bin/env python3

import logging
from threading import Lock
from requests_futures.sessions import FuturesSession


class Usermapper(object):
    """Build/maintain map of Slack usernames to GH usernames, based on a list
    "GitHub Username" custom field, which is (in LSSTC) "Xf2JS7M3C1".
    """

    usermap = {}
    userlist = []
    session = None
    usermap_initialized = False
    bot_token = None
    app_token = None
    field_id = None
    mutex = None

    def __init__(self, bot_token=None, app_token=None,
                 field_name="GitHub Username", max_workers=50):
        self.bot_token = bot_token
        self.app_token = app_token
        self.mutex = Lock()
        self.session = FuturesSession(max_workers=max_workers)
        self.field_id = self._get_field_id(field_name)
        self.userlist = self.rebuild_userlist()
        self.session.max_workers = min(max_workers, len(self.userlist))
        logging.debug("Building usermap.")
        self.rebuild_usermap()
        self.usermap_initialized = True
        logging.debug("Usermap built.")

    def github_for_slack_user(self, user):
        """Return the usermap entry for a given Slack user (which should be
        the GitHub Username field).  None if there is no match.
        """
        self._check_initialization()
        return self.usermap.get(user)

    def slack_for_github_user(self, user):
        """Given a GitHub Username, return the first Slack username that has
        that name in the GitHub Username field, or None.
        """
        for slacker in self.usermap:
            if self.usermap[slacker] == user:
                return slacker
        self._check_intialization()
        return None

    def rebuild_usermap(self):
        """Rebuild the entire Slack user -> GitHub user map.
        """
        newmap = {}
        futures = {}
        for user in self.userlist:
            futures[user["name"]] = self._retrieve_github_user_future(user)
        for user in futures:
            resp = self._slackcheck(futures[user])
            if "profile" in resp:
                ghuser = self._process_profile(resp["profile"])
                if ghuser:
                    self.mutex.acquire()
                    try:
                        newmap[user] = ghuser
                    finally:
                        self.mutex.release()
        self.usermap = newmap

    def rebuild_userlist(self):
        """Get all users of this Slack instance, with name and id.
        """
        params = {
            "Content-Type": "application/x-www-form/urlencoded",
            "token": self.bot_token
        }
        method = "users.list"
        moar = True
        userlist = []
        while moar:
            future = self._get_slack_future(method, params)
            retval = self._slackcheck(future)
            userlist = userlist + retval["members"]
            if ("response_metadata" in retval and
                "next_cursor" in retval["response_metadata"] and
                    retval["response_metadata"]["next_cursor"]):
                params["cursor"] = retval["response_metadata"]["next_cursor"]
            else:
                moar = False
        return [{"name": u["name"],
                 "id": u["id"]} for u in userlist]

    def _get_field_id(self, field_name):
        method = "team.profile.get"
        params = {
            "Content-Type": "application/x-www-form/urlencoded",
            "token": self.app_token,
        }
        future = self._get_slack_future(method, params)
        retval = self._slackcheck(future)
        if ("profile" in retval and retval["profile"] and
            "fields" in retval["profile"] and
                retval["profile"]["fields"]):
            for fld in retval["profile"]["fields"]:
                if ("label" in fld and "id" in fld and
                        fld["label"] == field_name):
                    return fld["id"]
        return None

    def _check_initialization(self):
        if not self.usermap_initialized:
            raise RuntimeError("Usermap not initialized.")

    def _retrieve_github_user_future(self, user):
        method = "users.profile.get"
        params = {
            "Content-Type": "application/x-www-form/urlencoded",
            "token": self.app_token,
            "user": user["id"]
        }
        return self._get_slack_future(method, params)

    def _process_profile(self, profile):
        ghname = None
        fid = self.field_id
        dname = profile["display_name_normalized"]
        if ("fields" in profile and profile["fields"] and
                fid in profile["fields"] and "value" in
                profile["fields"][fid]):
            ghname = profile["fields"][fid]["value"]
        logging.debug("Slack user %s -> GitHub user %r" % (dname, ghname))
        return ghname

    def _get_slack_future(self, method, params):
        url = "https://slack.com/api/" + method
        future = self.session.get(url, params=params)
        return future

    def _slackcheck(self, future):
        resp = future.result()
        resp.raise_for_status()
        retval = resp.json()
        if not retval["ok"]:
            errstr = "Slack API request '%s' failed: %s" % (resp.request.url,
                                                            retval["error"])
            raise RuntimeError(errstr)
        return retval
