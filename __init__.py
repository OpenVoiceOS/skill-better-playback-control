import random
from os.path import join, dirname
from adapt.intent import IntentBuilder
from mycroft.skills.core import intent_handler
from mycroft.messagebus.message import Message
from ovos_workshop.skills import OVOSSkill
from ovos_workshop.frameworks.playback import CommonPlayMediaType, CommonPlayPlaybackType, \
    CommonPlayMatchConfidence, OVOSCommonPlaybackInterface, \
    CommonPlayStatus, VideoPlayerType, AudioPlayerType
from ovos_workshop.frameworks.playback.youtube import is_youtube, \
    get_youtube_metadata, \
    get_youtube_video_stream
from ovos_utils.gui import is_gui_connected
from ovos_utils.json_helper import merge_dict
from ovos_utils.log import LOG
from pprint import pprint
from ovos_workshop.frameworks.playback.playlists import Playlist


class BetterPlaybackControlSkill(OVOSSkill):
    def initialize(self):
        # TODO skill settings for these values
        self.gui_only = False  # not recommended
        self.audio_only = False
        self.use_mycroft_gui = False  # send all playback to the plugin
        self.compatibility_mode = True
        self.media_type_fallback = True # if True send a Generic type query
        # when specific query fails, eg "play the News" -> news media not
        # found -> check other skills (youtube/iptv....)
        if self.use_mycroft_gui:
            audio = AudioPlayerType.MYCROFT
            video = VideoPlayerType.MYCROFT
        else:
            audio = AudioPlayerType.SIMPLE
            video = VideoPlayerType.SIMPLE
        self.common_play = OVOSCommonPlaybackInterface(
            bus=self.bus, backwards_compatibility=self.compatibility_mode,
            media_fallback=self.media_type_fallback, audio_player=audio,
            video_player=video, max_timeout=7, min_timeout=3)

        self.add_event("ovos.common_play.play", self.handle_play_request)

    def stop(self, message=None):
        # will stop any playback in VIDEO or AudioService
        try:
            return self.common_play.stop()
        except:
            pass

    # play xxx intents
    @intent_handler("play.intent")
    def generic_play(self, message):
        LOG.debug("Generic OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.GENERIC)

    @intent_handler("music.intent")
    def play_music(self, message):
        LOG.debug("Music OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.MUSIC)

    @intent_handler("video.intent")
    def play_video(self, message):
        LOG.debug("Video OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.VIDEO)

    @intent_handler("audiobook.intent")
    def play_audiobook(self, message):
        LOG.debug("AudioBook OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.AUDIOBOOK)

    @intent_handler("radio_drama.intent")
    def play_radio_drama(self, message):
        LOG.debug("Radio Theatre OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.RADIO_THEATRE)

    @intent_handler("behind_scenes.intent")
    def play_behind_scenes(self, message):
        LOG.debug("Behind the Scenes OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.BEHIND_THE_SCENES)

    @intent_handler("game.intent")
    def play_game(self, message):
        LOG.debug("Game OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.GAME)

    @intent_handler("radio.intent")
    def play_radio(self, message):
        LOG.debug("Radio OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.RADIO)

    @intent_handler("podcast.intent")
    def play_podcast(self, message):
        LOG.debug("Podcast OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.PODCAST)

    @intent_handler("news.intent")
    def play_news(self, message):
        LOG.debug("News OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.NEWS)

    @intent_handler("tv.intent")
    def play_tv(self, message):
        LOG.debug("TV OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.TV)

    @intent_handler("movie.intent")
    def play_movie(self, message):
        LOG.debug("Movie OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.MOVIE)

    @intent_handler("short_movie.intent")
    def play_short_movie(self, message):
        LOG.debug("Short Movie OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.SHORT_FILM)

    @intent_handler("silent_movie.intent")
    def play_silent_movie(self, message):
        LOG.debug("Silent Movie OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.SILENT_MOVIE)

    @intent_handler("bw_movie.intent")
    def play_bw_movie(self, message):
        LOG.debug("Black&White Movie OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.BLACK_WHITE_MOVIE)

    @intent_handler("movietrailer.intent")
    def play_trailer(self, message):
        LOG.debug("Trailer OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.TRAILER)

    @intent_handler("porn.intent")
    def play_adult(self, message):
        LOG.debug("Porn OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.ADULT)

    @intent_handler("comic.intent")
    def play_comic(self, message):
        LOG.debug("ComicBook OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.VISUAL_STORY)

    @intent_handler("documentaries.intent")
    def play_documentaries(self, message):
        LOG.debug("Documentaries OVOSCommonPlay match")
        self._play(message, CommonPlayMediaType.DOCUMENTARY)

    # playback control intents
    @intent_handler(IntentBuilder('NextCommonPlay')
                    .require('Next').require("Playing").optionally("Track"))
    def handle_next(self, message):
        self.common_play.play_next()

    @intent_handler(IntentBuilder('PrevCommonPlay')
                    .require('Prev').require("Playing").optionally("Track"))
    def handle_prev(self, message):
        self.common_play.play_prev()

    @intent_handler(IntentBuilder('PauseCommonPlay')
                    .require('Pause').require("Playing"))
    def handle_pause(self, message):
        self.common_play.pause()

    @intent_handler(IntentBuilder('ResumeCommonPlay')
                    .one_of('PlayResume', 'Resume').require("Playing"))
    def handle_resume(self, message):
        """Resume playback if paused"""
        self.common_play.resume()

    # playback selection
    def should_resume(self, phrase):
        if self.common_play.playback_status == CommonPlayStatus.PAUSED:
            if not phrase.strip() or \
                    self.voc_match(phrase, "Resume", exact=True) or \
                    self.voc_match(phrase, "Play", exact=True):
                return True
        return False

    def _play(self, message, media_type=CommonPlayMediaType.GENERIC):
        phrase = message.data.get("query", "")
        num = message.data.get("number", "")
        if num:
            phrase += " " + num

        # if media is currently paused, empty string means "resume playback"
        if self.should_resume(phrase):
            self.common_play.resume()
            return

        self.speak_dialog("just.one.moment", wait=True)

        self.enclosure.mouth_think()

        # reset common play playlist
        self.common_play.playlist = Playlist()

        # check if user said "play XXX audio only/no video"
        audio_only = False
        if self.voc_match(phrase, "audio_only"):
            audio_only = True
            # dont include "audio only" in search query
            phrase = self.remove_voc(phrase, "audio_only")

        # Now we place a query on the messsagebus for anyone who wants to
        # attempt to service a 'play.request' message.
        results = []
        for r in self.common_play.search(phrase, media_type=media_type):
            results += r["results"]

        # check if user said "play XXX audio only"
        if audio_only:
            LOG.info("audio only requested, forcing audio playback")
            for idx, r in enumerate(results):
                # force streams to be played audio only
                if r["playback"] != CommonPlayPlaybackType.AUDIO:
                    results[idx]["playback"] = CommonPlayPlaybackType.AUDIO
        # filter video results if GUI not connected
        elif self.audio_only or not is_gui_connected(self.bus):
            LOG.info("unable to use GUI, filtering non-audio results")
            results = [r for r in results
                       if r["playback"] == CommonPlayPlaybackType.AUDIO]

        if not results:
            self.speak_dialog("cant.play",
                              data={"phrase": phrase,
                                    "media_type": media_type})
            return

        best = self.select_best(results)
        self.common_play.play_media(best, results)
        self.enclosure.mouth_reset() # TODO display music icon in mk1
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
                # select only from VIDEO results if preference is set
                # WARNING this can effectively make it so that the same
                # skill is always selected
                gui_results = [r for r in ties if r["playback"] ==
                               CommonPlayPlaybackType.VIDEO]
                if len(gui_results):
                    selected = random.choice(gui_results)

            # TODO: Ask user to pick between ties or do it automagically
        else:
            selected = best
        LOG.debug(f"OVOSCommonPlay selected: {selected['skill_id']} - {selected['match_confidence']}")
        return selected

    # messagebus request to play track
    def handle_play_request(self, message):
        LOG.debug("Received external OVOS playback request")
        self.set_context("Playing")
        if message.data.get("tracks"):
            # backwards compat / old style
            playlist = disambiguation = message.data["tracks"]
            media = playlist[0]
        else:
            media = message.data.get("media")
            playlist = message.data.get("playlist") or [media]
            disambiguation = message.data.get("disambiguation") or [media]
        self.common_play.play_media(media, disambiguation, playlist)

    def shutdown(self):
        self.common_play.shutdown()


def create_skill():
    return BetterPlaybackControlSkill()
