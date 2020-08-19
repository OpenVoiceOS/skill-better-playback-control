# Copyright 2018 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import re
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.skills.audioservice import AudioService
from mycroft.audio import wait_while_speaking
from os.path import join, exists
from threading import Lock


STATUS_KEYS = ['track', 'artist', 'album', 'image']


class PlaybackControlSkill(MycroftSkill):
    def __init__(self):
        super(PlaybackControlSkill, self).__init__('Playback Control Skill')
        self.query_replies = {}     # cache of received replies
        self.query_extensions = {}  # maintains query timeout extensions
        self.has_played = False
        self.lock = Lock()

    def initialize(self):
        self.audio_service = AudioService(self.bus)
        self.add_event('play:query.response',
                       self.handle_play_query_response)
        self.add_event('play:status',
                       self.handle_song_info)
        self.gui.register_handler('next', self.handle_next)
        self.gui.register_handler('prev', self.handle_prev)

        self.clear_gui_info()
    # Handle common audio intents.  'Audio' skills should listen for the
    # common messages:
    #   self.add_event('mycroft.audio.service.next', SKILL_HANDLER)
    #   self.add_event('mycroft.audio.service.prev', SKILL_HANDLER)
    #   self.add_event('mycroft.audio.service.pause', SKILL_HANDLER)
    #   self.add_event('mycroft.audio.service.resume', SKILL_HANDLER)

    def clear_gui_info(self):
        """Clear the gui variable list."""
        # Initialize track info variables
        for k in STATUS_KEYS:
            self.gui[k] = ''

    @intent_handler(IntentBuilder('').require('Next').require("Track"))
    def handle_next(self, message):
        self.audio_service.next()

    @intent_handler(IntentBuilder('').require('Prev').require("Track"))
    def handle_prev(self, message):
        self.audio_service.prev()

    @intent_handler(IntentBuilder('').require('Pause'))
    def handle_pause(self, message):
        self.audio_service.pause()

    @intent_handler(IntentBuilder('').one_of('PlayResume', 'Resume'))
    def handle_play(self, message):
        """Resume playback if paused"""
        self.audio_service.resume()

    def stop(self, message=None):
        self.clear_gui_info()

        self.log.info('Audio service status: '
                      '{}'.format(self.audio_service.track_info()))
        if self.audio_service.is_playing:
            self.audio_service.stop()
            return True
        else:
            return False

    def converse(self, utterances, lang="en-us"):
        if (utterances and self.has_played and
                self.voc_match(utterances[0], "converse_resume", exact=True)):
            # NOTE:  voc_match() will overmatch (e.g. it'll catch "play next
            #        song" or "play Some Artist")
            self.audio_service.resume()
            return True
        else:
            return False

    @intent_handler(IntentBuilder('').require('Play').require('Phrase'))
    def play(self, message):
        self.speak_dialog("just.one.moment")

        # Remove everything up to and including "Play"
        # NOTE: This requires a Play.voc which holds any synomyms for 'Play'
        #       and a .rx that contains each of those synonyms.  E.g.
        #  Play.voc
        #      play
        #      bork
        #  phrase.rx
        #      play (?P<Phrase>.*)
        #      bork (?P<Phrase>.*)
        # This really just hacks around limitations of the Adapt regex system,
        # which will only return the first word of the target phrase
        utt = message.data.get('utterance')
        phrase = re.sub('^.*?' + message.data['Play'], '', utt).strip()
        self.log.info("Resolving Player for: "+phrase)
        wait_while_speaking()
        self.enclosure.mouth_think()

        # Now we place a query on the messsagebus for anyone who wants to
        # attempt to service a 'play.request' message.  E.g.:
        #   {
        #      "type": "play.query",
        #      "phrase": "the news" / "tom waits" / "madonna on Pandora"
        #   }
        #
        # One or more skills can reply with a 'play.request.reply', e.g.:
        #   {
        #      "type": "play.request.response",
        #      "target": "the news",
        #      "skill_id": "<self.skill_id>",
        #      "conf": "0.7",
        #      "callback_data": "<optional data>"
        #   }
        # This means the skill has a 70% confidence they can handle that
        # request.  The "callback_data" is optional, but can provide data
        # that eliminates the need to re-parse if this reply is chosen.
        #
        self.query_replies[phrase] = []
        self.query_extensions[phrase] = []
        self.bus.emit(message.forward('play:query', data={"phrase": phrase}))

        self.schedule_event(self._play_query_timeout, 1,
                            data={"phrase": phrase},
                            name='PlayQueryTimeout')

    def handle_play_query_response(self, message):
        with self.lock:
            search_phrase = message.data["phrase"]

            if ("searching" in message.data and
                    search_phrase in self.query_extensions):
                # Manage requests for time to complete searches
                skill_id = message.data["skill_id"]
                if message.data["searching"]:
                    # extend the timeout by 5 seconds
                    self.cancel_scheduled_event("PlayQueryTimeout")
                    self.schedule_event(self._play_query_timeout, 5,
                                        data={"phrase": search_phrase},
                                        name='PlayQueryTimeout')

                    # TODO: Perhaps block multiple extensions?
                    if skill_id not in self.query_extensions[search_phrase]:
                        self.query_extensions[search_phrase].append(skill_id)
                else:
                    # Search complete, don't wait on this skill any longer
                    if skill_id in self.query_extensions[search_phrase]:
                        self.query_extensions[search_phrase].remove(skill_id)
                        if not self.query_extensions[search_phrase]:
                            self.cancel_scheduled_event("PlayQueryTimeout")
                            self.schedule_event(self._play_query_timeout, 0,
                                                data={"phrase": search_phrase},
                                                name='PlayQueryTimeout')

            elif search_phrase in self.query_replies:
                # Collect all replies until the timeout
                self.query_replies[message.data["phrase"]].append(message.data)

    def _play_query_timeout(self, message):
        with self.lock:
            # Prevent any late-comers from retriggering this query handler
            search_phrase = message.data["phrase"]
            self.query_extensions[search_phrase] = []
            self.enclosure.mouth_reset()

            # Look at any replies that arrived before the timeout
            # Find response(s) with the highest confidence
            best = None
            ties = []
            self.log.debug("CommonPlay Resolution: {}".format(search_phrase))
            for handler in self.query_replies[search_phrase]:
                self.log.debug("    {} using {}".format(handler["conf"],
                                                        handler["skill_id"]))
                if not best or handler["conf"] > best["conf"]:
                    best = handler
                    ties = []
                elif handler["conf"] == best["conf"]:
                    ties.append(handler)

            if best:
                if ties:
                    # TODO: Ask user to pick between ties or do it
                    # automagically
                    pass

                # invoke best match
                self.gui.show_page("controls.qml", override_idle=True)
                self.log.info("Playing with: {}".format(best["skill_id"]))
                start_data = {"skill_id": best["skill_id"],
                              "phrase": search_phrase,
                              "callback_data": best.get("callback_data")}
                self.bus.emit(message.forward('play:start', start_data))
                self.has_played = True
            elif self.voc_match(search_phrase, "Music"):
                self.speak_dialog("setup.hints")
            else:
                self.log.info("   No matches")
                self.speak_dialog("cant.play", data={"phrase": search_phrase})

            if search_phrase in self.query_replies:
                del self.query_replies[search_phrase]
            if search_phrase in self.query_extensions:
                del self.query_extensions[search_phrase]

    def handle_song_info(self, message):
        changed = False
        for key in STATUS_KEYS:
            val = message.data.get(key, '')
            changed = changed or self.gui[key] != val
            self.gui[key] = val

        if changed:
            self.log.info('\n-->Track: {}\n-->Artist: {}\n-->Image: {}'
                          ''.format(self.gui['track'], self.gui['artist'],
                                    self.gui['image']))


def create_skill():
    return PlaybackControlSkill()
