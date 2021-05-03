# -*- coding: utf-8 -*-
"""
    MindiGO Kodi addon
    Copyright (C) 2020 ratcashdev
    Copyright (C) 2020 MrDini

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>
"""

import sys
from base64 import b64decode
from datetime import datetime, timedelta
from random import choice

import requests


# the following 3 methods were taken fom routines
def decrypt_string(_input):
    # type: (str)
    return str(b64decode(_input[6:])[7:].decode("utf-8"))


def random_uagent():
    # type: None -> str
    return choice(
        [
            # PC - Chrome
            "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36",
            # PC - Firefox
            "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:59.0) Gecko/20100101 Firefox/59.0",
            "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0",
            "Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0",
        ]
    )


def request_page(url, **kwargs):
    # type: (str, *, str, dict, dict, dict, dict, dict, bool)
    """
    Basic request routine, supports GET and POST requests.
    If the `data` keyword argument is present, defaults to POST, otherwise GET request.
    """
    user_agent = kwargs.get("user_agent", random_uagent())
    params = kwargs.get("params")
    headers = kwargs.get("headers", {})
    additional_headers = kwargs.get("additional_headers", {})
    cookies = kwargs.get("cookies")
    data = kwargs.get("data")
    allow_redirects = kwargs.get("allow_redirects")
    headers.update({"User-Agent": user_agent})
    headers.update(additional_headers)

    if not data:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            allow_redirects=allow_redirects,
        )
    else:
        response = requests.post(
            url,
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            allow_redirects=allow_redirects,
        )

    return response


"""
 v3 api based on the current web
 this class was extracted so that there are no dependencies on XBMC and testing is easier
"""


class MindigoClient:

    API_BASE = "470098bXNyZXBvIGh0dHBzOi8vbWluZGlndHZnby5odS9zYi8="
    MAIN_URI = "470098bXNyZXBvIGh0dHBzOi8vdHYubWluZGlnby5odS8="
    APP_ID = "470098bXNyZXBvIGVubjlpbW1kbTF2eXU3eXVwZG5raWVkY2g1d21naTRj"

    # contains the value of the JSESSIONID cookie returned after a successful login
    session = None

    # pre-decoded urls
    web_url = decrypt_string(MAIN_URI)
    api_url = decrypt_string(API_BASE)

    HEADERS = {
        "x-application-id": decrypt_string(APP_ID),
        "x-platform": "web",
        "x-os-name": "Windows",
        "x-os-version": "10",
        "x-browser-name": "undefined",
        "x-browser-version": "undefined",
        "Origin": web_url,
    }

    def login(self, username, password):
        url = "%slogin?deviceType=WEB" % self.api_url
        response = request_page(
            url,
            headers=self.HEADERS,
            additional_headers={"Referer": "%s/home" % self.web_url},
            data={"username": username, "password": password},
        )

        if response.status_code == 200:
            self.session = response.cookies.get("JSESSIONID")
        # print("cookie: %s" % self.session)
        return response

    """
	   visibility_rights either 'PLAY' or 'PREVIEW'
	"""

    def get_channels(self, visibility_rights="PREVIEW"):
        url = "%schannel/all?vf=dash&visibilityRights=%s" % (
            self.api_url,
            visibility_rights,
        )
        response = request_page(
            url,
            headers=self.HEADERS,
            cookies=dict(JSESSIONID=self.session),
            additional_headers={"Referer": "%s/epg" % self.web_url},
        )
        return {e["id"]: e for e in response.json()}

    def get_visible_channels(self):
        return self.get_channels("PLAY")

    def get_epg(
        self,
        channels,
        start=datetime.now() - timedelta(hours=1),
        end=datetime.now() + timedelta(hours=1),
    ):
        url = (
            "%sepg/channels?startTime=%sZ&endTime=%sZ&channelIds=%s&vf=dash&visibilityRights=PLAY"
            % (self.api_url, start.isoformat(), end.isoformat(), channels)
        )
        response = request_page(
            url,
            headers=self.HEADERS,
            cookies={"JSESSIONID": self.session},
            additional_headers={"Referer": "%s/epg" % self.web_url},
        )
        return response.json()

    def get_live_epg(self, channels="8,25,66,41,42,10,39,15,16,49"):
        # consider only LIVE elements
        return [e for e in self.get_epg(channels) if e.get("state") == "LIVE"]

    def get_video_details(self, vod_asset_id):
        url = "%sasset/%s?vf=dash&&deviceType=WEB" % (self.api_url, vod_asset_id)
        print(url)
        response = request_page(
            url,
            headers=self.HEADERS,
            cookies=dict(JSESSIONID=self.session),
            additional_headers={"Referer": "%s/epg/channels" % self.web_url},
        )
        return response.json()

    def get_video_content_url(self, vod_asset_id):
        return (
            self.get_video_details(vod_asset_id)
            .get("epgEvent")
            .get("channel")
            .get("contentUrl")
        )
