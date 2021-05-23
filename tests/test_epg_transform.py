import unittest
import json

from app import epg_transform

class TestEpgTransform(unittest.TestCase):

    def test_epg_transform(self):
        with open('json/multi-channels-epg.json') as epg_file:
            epg = json.load(epg_file)
            with open('json/channels.json') as channels_file:
                channels = {e["id"] : e for e in json.load(channels_file)}
                res = epg_transform.make_xml_guide(channels, epg)
                epg_transform.write_str('./','delete-mindigo-xmltv.xml', res)
        # self.assertEqual(sum([1, 2, 3]), 6, "Should be 6")

    def test_m3u_transform(self):
        with open('json/channels.json') as channels_file:
            channels = {e["id"] : e for e in json.load(channels_file)}
            res = epg_transform.make_m3u(channels)
            epg_transform.write_str('./','delete-mindigo-channels.m3u8', res)


if __name__ == '__main__':
    unittest.main()
