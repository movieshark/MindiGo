# -*- coding: utf-8 -*-
"""
    MindiGO Kodi addon
    Copyright (C) 2019 Mr Dini, ratcashdev

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
from mindigo_client import MindigoClient
from urlparse import parse_qsl
from mrdini.routines import routines
import xbmcaddon
from xbmcplugin import endOfDirectory, setContent
import xbmcgui

utils = routines.Utils(xbmcaddon.Addon())
client = MindigoClient()

# TODO move to routines (?)
def play_dash(handle, url, _type, **kwargs):
    name = kwargs.get("name")
    icon = kwargs.get("icon")
    description = kwargs.get("description")
    user_agent = kwargs.get("user_agent", routines.random_uagent())

    listitem = xbmcgui.ListItem(label=name, thumbnailImage=icon)
    listitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
    listitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    listitem.setMimeType('application/dash+xml')
    listitem.setProperty('inputstream.adaptive.stream_headers', "User-Agent=%s" % user_agent)
    listitem.setContentLookup(False)
    listitem.setInfo(type=_type, infoLabels={"Title": name, "Plot": description})
    xbmc.Player().play(url, listitem)

def setupSession():
    if (
        client.session is None
        and utils.get_setting("session") != None
        and int(time()) - int(utils.get_setting("last_ts") or 0) < int(1200)
    ):
        client.session = utils.get_setting("session")
        utils.set_setting("last_ts", str(int(time())))
        return

    utils.set_setting("session", login())
    utils.set_setting("last_ts", str(int(time())))

def login():
    if not all([utils.get_setting("username"), utils.get_setting("password")]):
        utils.create_notification("Kérlek add meg email címed és jelszavad!")
        utils.open_settings()
        exit(0)

    try:
        response = client.login(utils.get_setting("username"), utils.get_setting("password"))
        if response.status_code in [400, 404]:
            utils.create_ok_dialog(
                "Bejelentkezésed sikertelen volt. Biztosan jól adtad meg az email címed és jelszavad?"
            )
            utils.open_settings()
            exit(1)
        elif response.status_code != 200:
            utils.create_ok_dialog(
                "Ennek a hibának nem kellett volna előfordulnia. Kérlek jelezd a fejlesztőnek"
                ", hogy az addon hibára futott bejelentkezésnél. A szerver válasza: %i\nEsetleg próbáld újra később, lehet, hogy a szerver túlterhelt."
                % (response.status_code)
            )
            exit(1)
    except RuntimeError as e:
        raise routines.Error(e)
    utils.set_setting("session", client.session)
    utils.create_notification("Sikeres bejelentkezés")
    return client.session


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
    all_channels = client.get_visible_channels()
    channel_ids = [str(k) for k,v in all_channels.items()]
    channel_list = ",".join(channel_ids)
    epg = client.get_live_epg(channel_list)
    for program in epg:
        if (
            utils.get_setting("display_epg") != "2"
        ):
            name = "%s[CR][COLOR gray]%s[/COLOR]" % (
                all_channels[program["channelId"]]["displayName"].encode("utf-8"),
                program["title"].encode("utf-8"),
            )
        else:
            name = program["title"].encode("utf-8")

	if program.get("imageUrl"):
            fan_art = "%s%s" % (client.web_url, program.get("imageUrl").encode("utf-8"))
        else:
            fan_art=utils.fanart

        routines.add_item(
            *sys.argv[:2],
            name=name,
	    description=(program.get("description") or "").encode("utf-8"),
            action="translate_link",
            icon="%s%s" % (client.web_url, program["imageUrls"]["channel_logo"]),
            id=program["id"],
            extra=program["vodAssetId"],
            fanart=fan_art,
            type="video",
            refresh=True,
            is_directory=False,
            is_livestream=True
        )
    setContent(int(sys.argv[1]), "tvshows")


def translate_link(id, slug, name, icon, desc):
    url = client.get_video_content_url(slug)

    if url == None:
        message = ["A szerver nem tudott mit kezdeni a kéréssel."]
        utils.create_ok_dialog("[CR]".join(message))
        exit()

    
    # if data["data"].get("drmkey"):
    #     utils.create_notification(
    #         "DRM védett tartalom. Az addon ezek lejátszására nem képes."
    #     )
    #     exit()

    # if utils.get_setting("display_epg") == "1":
    #     name = name.split("[CR]", 1)[0]

    play_dash(
        int(sys.argv[1]),
        url,
        "video",
        user_agent=utils.get_setting("user_agent"),
        name=name,
        icon=icon,
        description=desc
    )


if __name__ == "__main__":
    params = dict(parse_qsl(sys.argv[2].replace("?", "")))
    action = params.get("action")
    setupSession()

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
            params.get("descr"),
        )
