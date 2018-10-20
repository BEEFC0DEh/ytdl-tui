#!/usr/bin/env python
# encoding: utf-8
import json
import npyscreen
import sys
from subprocess import run
from subprocess import check_output


class Fmt(object):
    def __init__(self, fmtId, text):
        self.fmtId = fmtId
        self.text = text


class FmtList(npyscreen.SelectOne):
    def __init__(self, *args, **keywords):
        super(FmtList, self).__init__(*args, **keywords)

    def display_value(self, vl):
        return '{}'.format(vl.text)

class FormatsForm(npyscreen.ActionForm):
    audio_fmts = []
    video_fmts = []
    url = 'https://www.youtube.com/watch?v=2MpUj-Aua48'

    @staticmethod
    def get_size_string(kilobytes):
        unit = 'KiB'
        if kilobytes >= 1024:
            kilobytes = kilobytes / 1024
            unit = 'MiB'

        if kilobytes >= 1024:
            kilobytes = kilobytes / 1024
            unit = 'GiB'

        return '{}{}'.format(round(kilobytes, 2), unit)

    def append_fmt_to_list(self, lst, fmtId, description, bitrate, kilobytes):
        sizeString = self.get_size_string(kilobytes)
        s = '{}\t- {}\t{}kbps'.format(fmtId, description, bitrate).expandtabs(2)
        s = '{}\t{}'.format(s, sizeString).expandtabs(8)
        lst.append(Fmt(fmtId, s))

    def download_json(self):
        if len(sys.argv) > 1:
            self.url = sys.argv[1]

        print('Querying formats for {}'.format(self.url))
        result = check_output(['youtube-dl -j {}'.format(self.url)], shell=True).decode('utf-8')
        # result = run( [ 'youtube-dl -j {}'.format(self.url) ], shell=True, capture_output=True, text=True )
        # j = json.loads(result.stdout)
        return json.loads(result)

    def fill_models(self):
        j = self.download_json()
        duration = j['duration']
        fmts = j['formats']

        for fmt in fmts:
            try:
                fmt_id = fmt['format_id']
                size = fmt['filesize']
                kilobytes = size / 1024
                bitrate = round((kilobytes / duration) * 8)

                if fmt['vcodec'] and fmt['vcodec'] != 'none':
                    height = fmt['height']
                    desc = '{}p'.format(height)
                    self.append_fmt_to_list(self.video_fmts, fmt_id, desc, bitrate, kilobytes)
                else:
                    acodec = fmt['acodec'][:4]
                    self.append_fmt_to_list(self.audio_fmts, fmt_id, acodec, bitrate, kilobytes)
            except KeyError:
                print('Unknown id/codec.')

    def create(self):
        self.fill_models()

        self.add(npyscreen.FixedText, value="Video", max_width=40, editable=False)
        self.video = self.add(FmtList, value=[0], name="Video", max_width=40, max_height=16,
                            values=self.video_fmts, scroll_exit=True, exit_right=True)

        self.add(npyscreen.FixedText, value="Audio", max_width=40, editable=False, relx=42, rely=2)
        self.audio = self.add(FmtList, value=[0], name="Audio", max_width=40, max_height=16,
                            values=self.audio_fmts, scroll_exit=True, exit_left=True, relx=42, rely=3)

    def on_ok(self):
        self.parentApp.setNextForm(None)
        import curses
        curses.endwin()

        ids = [self.video_fmts[self.video.value[0]].fmtId,
               self.audio_fmts[self.audio.value[0]].fmtId]
        prefs = '{}+{}'.format(ids[0], ids[1])
        print(prefs)
        run(["mpv --term-status-msg='Video bitrate: ${{video-bitrate}}, audio bitrate: ${{audio-bitrate}}' --ytdl-format {} {}".format(
            prefs, self.url)], shell=True)

    def on_cancel(self):
        self.parentApp.setNextForm(None)

class YtdlTui(npyscreen.NPSAppManaged):
    STARTING_FORM = 'FORMATS'

    def onStart(self):
        self.addForm('FORMATS', FormatsForm, name="Select preferred formats", minimum_lines=20)


if __name__ == "__main__":
    App = YtdlTui()
    App.run()
