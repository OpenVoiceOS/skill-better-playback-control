import random
from os.path import join, dirname
from adapt.intent import IntentBuilder
from mycroft.skills.core import intent_handler
from mycroft.messagebus.message import Message
from ovos_workshop.skills import OVOSSkill
from ovos_workshop.frameworks.cps import CPSMatchType, CPSPlayback, \
    CPSMatchConfidence, BetterCommonPlayInterface, CPSTrackStatus
from ovos_workshop.frameworks.cps.youtube import is_youtube, \
    get_youtube_metadata, \
    get_youtube_video_stream
from ovos_utils.gui import is_gui_connected, GUIInterface
from ovos_utils.json_helper import merge_dict
from ovos_utils.log import LOG
from pprint import pprint


class BetterPlaybackControlSkill(OVOSSkill):

    def initialize(self):
        # TODO skill settings for these values
        self.gui_only = False  # not recommended
        self.audio_only = False
        self.compatibility_mode = False
        self.media_type_fallback = True
        self.cps = BetterCommonPlayInterface(
            bus=self.bus, backwards_compatibility=self.compatibility_mode,
            media_fallback=self.media_type_fallback,
            max_timeout=7, min_timeout=3)

        self.add_event("better_cps.play", self.handle_play_request)

    def stop(self, message=None):
        # will stop any playback in GUI or AudioService
        return self.cps.stop()

    # play xxx intents
    @intent_handler("play.intent")
    def generic_play(self, message):
        LOG.debug("Generic BetterCPS match")
        self._play(message, CPSMatchType.GENERIC)

    @intent_handler("music.intent")
    def play_music(self, message):
        LOG.debug("Music BetterCPS match")
        self._play(message, CPSMatchType.MUSIC)

    @intent_handler("video.intent")
    def play_video(self, message):
        LOG.debug("Video BetterCPS match")
        self._play(message, CPSMatchType.VIDEO)

    @intent_handler("audio.intent")
    def play_audio(self, message):
        LOG.debug("Audio BetterCPS match")
        try:
            self._play(message, CPSMatchType.AUDIO)
        except:
            self._play(message, CPSMatchType.MUSIC)

    @intent_handler("audiobook.intent")
    def play_audiobook(self, message):
        LOG.debug("AudioBook BetterCPS match")
        self._play(message, CPSMatchType.AUDIOBOOK)

    @intent_handler("radio_drama.intent")
    def play_radio_drama(self, message):
        LOG.debug("Radio Theatre BetterCPS match")
        # TODO new type in next ovos_utils alpha release
        try:
            self._play(message, CPSMatchType.RADIO_THEATRE)
        except:
            self._play(message, CPSMatchType.AUDIOBOOK)

    @intent_handler("behind_scenes.intent")
    def play_behind_scenes(self, message):
        LOG.debug("Behind the Scenes BetterCPS match")
        # TODO new type in next ovos_utils alpha release
        try:
            self._play(message, CPSMatchType.BEHIND_THE_SCENES)
        except:
            self._play(message, CPSMatchType.VIDEO)

    @intent_handler("game.intent")
    def play_game(self, message):
        LOG.debug("Game BetterCPS match")
        self._play(message, CPSMatchType.GAME)

    @intent_handler("radio.intent")
    def play_radio(self, message):
        LOG.debug("Radio BetterCPS match")
        self._play(message, CPSMatchType.RADIO)

    @intent_handler("podcast.intent")
    def play_podcast(self, message):
        LOG.debug("Podcast BetterCPS match")
        self._play(message, CPSMatchType.PODCAST)

    @intent_handler("news.intent")
    def play_news(self, message):
        LOG.debug("News BetterCPS match")
        self._play(message, CPSMatchType.NEWS)

    @intent_handler("tv.intent")
    def play_tv(self, message):
        LOG.debug("TV BetterCPS match")
        self._play(message, CPSMatchType.TV)

    @intent_handler("movie.intent")
    def play_movie(self, message):
        LOG.debug("Movie BetterCPS match")
        self._play(message, CPSMatchType.MOVIE)

    @intent_handler("short_movie.intent")
    def play_short_movie(self, message):
        LOG.debug("Short Movie BetterCPS match")
        try:
            self._play(message, CPSMatchType.SHORT_FILM)
        except:
            self._play(message, CPSMatchType.MOVIE)

    @intent_handler("silent_movie.intent")
    def play_silent_movie(self, message):
        LOG.debug("Silent Movie BetterCPS match")
        try:
            self._play(message, CPSMatchType.SILENT_MOVIE)
        except:
            self._play(message, CPSMatchType.MOVIE)

    @intent_handler("bw_movie.intent")
    def play_bw_movie(self, message):
        LOG.debug("Black&White Movie BetterCPS match")
        try:
            self._play(message, CPSMatchType.BLACK_WHITE_MOVIE)
        except:
            self._play(message, CPSMatchType.MOVIE)

    @intent_handler("movietrailer.intent")
    def play_trailer(self, message):
        LOG.debug("Trailer BetterCPS match")
        self._play(message, CPSMatchType.TRAILER)

    @intent_handler("porn.intent")
    def play_adult(self, message):
        LOG.debug("Porn BetterCPS match")
        self._play(message, CPSMatchType.ADULT)

    @intent_handler("comic.intent")
    def play_comic(self, message):
        LOG.debug("ComicBook BetterCPS match")
        self._play(message, CPSMatchType.VISUAL_STORY)

    @intent_handler("documentaries.intent")
    def play_documentaries(self, message):
        LOG.debug("Documentaries BetterCPS match")
        self._play(message, CPSMatchType.DOCUMENTARY)

    # playback control intents
    @intent_handler(IntentBuilder('NextCommonPlay')
                    .require('Next').require("Playing").optionally("Track"))
    def handle_next(self, message):
        self.cps.play_next()

    @intent_handler(IntentBuilder('PrevCommonPlay')
                    .require('Prev').require("Playing").optionally("Track"))
    def handle_prev(self, message):
        self.cps.play_prev()

    @intent_handler(IntentBuilder('PauseCommonPlay')
                    .require('Pause').require("Playing"))
    def handle_pause(self, message):
        self.cps.pause()

    @intent_handler(IntentBuilder('ResumeCommonPlay')
                    .one_of('PlayResume', 'Resume').require("Playing"))
    def handle_resume(self, message):
        """Resume playback if paused"""
        self.cps.resume()

    # playback selection
    def should_resume(self, phrase):
        if self.cps.playback_status == CPSTrackStatus.PAUSED:
            if not phrase.strip() or \
                    self.voc_match(phrase, "Resume", exact=True) or \
                    self.voc_match(phrase, "Play", exact=True):
                return True
        return False

    def _play(self, message, media_type=CPSMatchType.GENERIC):
        phrase = message.data.get("query", "")
        num = message.data.get("number", "")
        if num:
            phrase += " " + num

        # if media is currently paused, empty string means "resume playback"
        if self.should_resume(phrase):
            self.cps.resume()
            return

        self.speak_dialog("just.one.moment", wait=True)

        self.enclosure.mouth_think()

        # Now we place a query on the messsagebus for anyone who wants to
        # attempt to service a 'play.request' message.
        results = []
        for r in self.cps.search(phrase, media_type=media_type):
            results += r["results"]

        # filter GUI only results if GUI not connected
        gui_connected = is_gui_connected(self.bus)
        if self.audio_only or not gui_connected:
            results = [r for r in results if r["playback"] != CPSPlayback.GUI]

        if not results:
            self.speak_dialog("cant.play",
                              data={"phrase": phrase,
                                    "media_type": media_type})
            return

        best = self.select_best(results)
        self.cps.process_search(best, results)
        self.enclosure.mouth_reset()
        self.set_context("Playing")

    def select_best(self, results):
        # Look at any replies that arrived before the timeout
        # Find response(s) with the highest confidence
        best = None
        ties = []
        for handler in results:
            if not best or handler['match_confidence'] > best['match_confidence']:
                best = handler
                ties = [best]
            elif handler['match_confidence'] == best['match_confidence']:
                ties.append(handler)

        if ties:
            # select randomly
            selected = random.choice(ties)

            if self.gui_only:
                # select only from GUI results if preference is set
                # WARNING this can effectively make it so that the same
                # skill is always selected
                gui_results = [r for r in ties if r["playback"] ==
                               CPSPlayback.GUI]
                if len(gui_results):
                    selected = random.choice(gui_results)

            # TODO: Ask user to pick between ties or do it automagically
        else:
            selected = best
        LOG.debug(f"BetterCPS selected: {selected['skill_id']} - {selected['match_confidence']}")
        return selected

    # messagebus request to play track
    def handle_play_request(self, message):
        tracks = message.data["tracks"]
        self.set_context("Playing")
        # TODO cps.queue / playlist support
        self.cps.update_playlist(tracks)
        self.cps.update_search_results(tracks)
        self.cps.play(tracks[0])

    def shutdown(self):
        self.cps.shutdown()


def create_skill():
    return BetterPlaybackControlSkill()
