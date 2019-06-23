# -*- coding: utf-8 -*-
"""
    MindiGO Kodi addon
    Copyright (C) 2019 Mr Dini

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
from time import time
from urlparse import parse_qsl
from mrdini.routines import routines
import xbmcaddon
from xbmcplugin import endOfDirectory, setContent

utils = routines.Utils(xbmcaddon.Addon())

API_BASE = "470098bXNyZXBvIGh0dHBzOi8vYXBpLm1pbmRpZ28uaHUvYXBpLw=="
MAIN_URI = "470098bXNyZXBvIGh0dHBzOi8vdHYubWluZGlnby5odS8="
APP_ID = "470098bXNyZXBvIGVubjlpbW1kbTF2eXU3eXVwZG5raWVkY2g1d21naTRj"
VERSION = "1.0.22"

HEADERS = {
    "x-application-id": routines.decrypt_string(APP_ID),
    "x-app-version": VERSION,
    "x-platform": "web",
    "x-os-name": "Windows",
    "x-os-version": "10",
    "x-browser-name": "undefined",
    "x-browser-version": "undefined",
    "Origin": routines.decrypt_string(MAIN_URI),
}


def get_token():
    if int(time()) - int(utils.get_setting("token_updated_at")) < int(
        utils.get_setting("token_lifetime") or 86400
    ):
        return utils.get_setting("token")
    if not utils.get_setting("refresh_token"):
        # should be first start or reset
        if not utils.get_setting("user_agent"):
            # if not already set, we set one and keep it forever
            utils.set_setting("user_agent", routines.random_uagent())
        return login()
    token = extend_token()
    utils.set_setting("token_updated_at", str(int(time())))
    return token


def login():
    if not all([utils.get_setting("username"), utils.get_setting("password")]):
        utils.create_notification("Kérlek add meg email címed és jelszavad!")
        utils.open_settings()
        exit(0)
    response = routines.request_page(
        "%sv2/user/login" % (routines.decrypt_string(API_BASE)),
        user_agent=utils.get_setting("user_agent"),
        headers=HEADERS,
        additional_headers={
            "Referer": "%s?popup=bejelentkezes" % (routines.decrypt_string(MAIN_URI))
        },
        data={
            "email": utils.get_setting("username"),
            "password": utils.get_setting("password"),
            "platform": "web",
            "app_version": VERSION,
        },
    )
    if response.status_code in [400, 404]:
        utils.create_ok_dialog(
            "Bejelentkezésed sikertelen volt. Biztosan jól adtad meg az email címed és jelszavad?"
        )
        utils.open_settings()
        exit(1)
    elif response.status_code != 200:
        utils.create_ok_dialog(
            "Ennek a hibának nem kellett volna előfordulnia. Kérlek jelezd a fejlesztőnek"
            ", hogy az addon hibára futott bejelentkezésnél. A szerver válasza: %i\nEsetleg próbáld újra kásőbb, lehet, hogy a szerver túlterhelt."
            % (response.status_code)
        )
        exit(1)
    try:
        data = response.json()
    except Exception as e:
        raise routines.Error(e)
    utils.set_setting("refresh_token", data["refreshToken"].encode("utf-8"))
    utils.set_setting("token", data["token"].encode("utf-8"))
    utils.create_notification("Sikeres bejelentkezés")
    utils.set_setting("token_updated_at", str(int(time())))
    return data["token"].encode("utf-8")


def extend_token():
    response = routines.request_page(
        "%sv1/user/session/extend" % (routines.decrypt_string(API_BASE)),
        user_agent=utils.get_setting("user_agent"),
        headers=HEADERS,
        additional_headers={"Referer": routines.decrypt_string(MAIN_URI)},
        data={
            "refreshToken": utils.get_setting("refresh_token"),
            "platform": "web",
            "app_version": VERSION,
        },
    )
    if response.status_code != 200:
        utils.create_ok_dialog(
            "Sikertelen a token frissítése. Próbálkozzon jelszót változtatni!\n"
            "Amennyiben a probléma továbbra is fennállna, jelezze a fejlesztőnek."
        )
        exit(1)
    try:
        data = response.json()
    except Exception as e:
        raise routines.Error(e)
    utils.set_setting("refresh_token", data["refreshToken"].encode("utf-8"))
    utils.set_setting("token", data["token"].encode("utf-8"))
    utils.create_notification("Sikeres token frissítés")
    return data["token"].encode("utf-8")


def main_window():
    routines.add_item(
        *sys.argv[:2],
        name="Élő Csatornakínálat",
        action="channels",
        is_directory=True,
        fanart=utils.fanart,
        icon="https://i.imgur.com/n0AbCQn.png"
    )
    routines.add_item(
        *sys.argv[:2],
        name="Bejelentkezési gyorsítótár törlése",
        description="A kiegészítő, a haladó beállításokban megadott időközönként bejelentkezik, majd lementi a kapott bejelentkezési adatokat."
        "Ha valami oknál fogva a kiegészítő nem működik, érdemes az opcióval próbálkozni.",
        action="clear_login",
        is_directory=False,
        fanart=utils.fanart,
        icon="https://i.imgur.com/RoT6O6r.png"
    )
    routines.add_item(
        *sys.argv[:2],
        name="Beállítások",
        description="Addon beállításai",
        action="settings",
        is_directory=False,
        fanart=utils.fanart,
        icon="https://i.imgur.com/MI42pRz.png"
    )
    routines.add_item(
        *sys.argv[:2],
        name="A kiegészítőről",
        description="Egyéb infók",
        action="about",
        is_directory=False,
        fanart=utils.fanart,
        icon="https://i.imgur.com/bKJK0nc.png"
    )


def live_window():
    response = routines.request_page(
        "%sv2/channels/live" % (routines.decrypt_string(API_BASE)),
        user_agent=utils.get_setting("user_agent"),
        headers={
            "Referer": "%scsatornak" % (routines.decrypt_string(MAIN_URI)),
            "x-application-id": routines.decrypt_string(APP_ID),
            "x-access-token": get_token(),
        },
    )
    for channel in response.json()["data"]["available"]:
        if channel.get("epg") and channel["epg"].get("title"):
            name = "%s[CR][COLOR gray]%s[/COLOR]" % (
                channel.get("name").encode("utf-8"),
                channel["epg"]["title"].encode("utf-8"),
            )
        else:
            name = channel.get("name").encode("utf-8")
        routines.add_item(
            *sys.argv[:2],
            name=name,
            action="translate_link",
            icon=channel.get("logoLink"),
            id=channel.get("id"),
            extra=channel.get("slug"),
            fanart=utils.fanart,
            type="video",
            refresh=True,
            is_directory=False,
            is_livestream=True
        )
    setContent(int(sys.argv[1]), "tvshows")


def translate_link(id, slug, name, icon):
    response = routines.request_page(
        "%sv2/streams/live?content_id=%s&language=hu&type=hls"
        % (routines.decrypt_string(API_BASE), id),
        user_agent=utils.get_setting("user_agent"),
        headers={
            "Referer": "%scsatornak/%s" % (routines.decrypt_string(MAIN_URI), slug),
            "x-application-id": routines.decrypt_string(APP_ID),
            "x-access-token": get_token(),
        },
    )
    if response.status_code == 400:
        message = ["A szerver nem tudott mit kezdeni a kéréssel."]
        if response.json().get("errorCode") == 10930:
            message.append("Túl gyorsan váltogatsz a csatornák közt, várj 5 mp-et!")
        if response.json().get("errorMessage"):
            message.append("Hibaüzenet: [COLOR darkred]%s[/COLOR]" % (response.json()["errorMessage"].encode("utf-8")))
        utils.create_ok_dialog("[CR]".join(message))
        exit()
    elif response.status_code != 200:
        utils.create_ok_dialog(
            "Lejátszás sikertelen ismeretlen okból.\nA szerver válasza: (%i) %s"
            % (response.status_code, response.content.encode("utf-8"))
        )
        exit(1)

    try:
        data = response.json()
    except Exception as e:
        raise routines.Error(e)

    if not data.get("data", {}).get("url"):
        utils.create_ok_dialog("Ehhez a médiához nem tartozik lejátszási link.")
        exit()

    if data["data"].get("drmkey"):
        utils.create_notification(
            "DRM védett tartalom. Az addon ezek lejátszására nem képes."
        )
        exit()

    routines.play(
        int(sys.argv[1]),
        data["data"]["url"],
        "video",
        user_agent=utils.get_setting("user_agent"),
        name=name,
        icon=icon,
    )


if __name__ == "__main__":
    params = dict(parse_qsl(sys.argv[2].replace("?", "")))
    action = params.get("action")
    if action is None:
        if utils.get_setting("is_firstrun") == "true":
            utils.set_setting("is_firstrun", "false")
            from utils.informations import text

            utils.create_textbox(text % (utils.addon_name, utils.version))
            utils.create_ok_dialog("Kérlek jelentkezz be az addon használatához!")
            utils.open_settings()
        main_window()
        endOfDirectory(int(sys.argv[1]))
    if action == "channels":
        live_window()
        endOfDirectory(int(sys.argv[1]))
    if action == "clear_login":
        utils.set_setting("refresh_token", "")
        utils.set_setting("token_updated_at", "0")
        utils.create_notification("Gyorsítótár sikeresen törölve.")
    if action == "settings":
        utils.open_settings()
    if action == "about":
        from utils.informations import text

        utils.create_textbox(text % (utils.addon_name, utils.version))
    if action == "translate_link":
        translate_link(
            params.get("id"),
            params.get("extra"),
            params.get("name"),
            params.get("icon"),
        )
