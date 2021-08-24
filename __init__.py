import random
from os.path import join, dirname, isfile

from adapt.intent import IntentBuilder
from mycroft.skills.core import intent_handler
from ovos_utils.gui import can_use_gui
from ovos_utils.log import LOG
from ovos_workshop.frameworks.playback import CommonPlayMediaType, \
    CommonPlayPlaybackType, \
    OVOSCommonPlaybackInterface, \
    CommonPlayStatus, VideoPlayerType, AudioPlayerType
from ovos_workshop.frameworks.playback.playlists import Playlist
from ovos_workshop.skills import OVOSSkill
from padacioso import IntentContainer
from ovos_workshop.frameworks.playback.youtube import is_youtube, \
    get_youtube_audio_stream, get_youtube_video_stream
from ovos_workshop.frameworks.playback.deezer import is_deezer,\
    get_deezer_audio_stream
import deezeridu


class BetterPlaybackControlSkill(OVOSSkill):
    intent2media = {
        "music": CommonPlayMediaType.MUSIC,
        "video": CommonPlayMediaType.VIDEO,
        "audiobook": CommonPlayMediaType.AUDIOBOOK,
        "radio": CommonPlayMediaType.RADIO,
        "radio_drama": CommonPlayMediaType.RADIO_THEATRE,
        "game": CommonPlayMediaType.GAME,
        "tv": CommonPlayMediaType.TV,
        "podcast": CommonPlayMediaType.PODCAST,
        "news": CommonPlayMediaType.NEWS,
        "movie": CommonPlayMediaType.MOVIE,
        "short_movie": CommonPlayMediaType.SHORT_FILM,
        "silent_movie": CommonPlayMediaType.SILENT_MOVIE,
        "bw_movie": CommonPlayMediaType.BLACK_WHITE_MOVIE,
        "documentaries": CommonPlayMediaType.DOCUMENTARY,
        "comic": CommonPlayMediaType.VISUAL_STORY,
        "movietrailer": CommonPlayMediaType.TRAILER,
        "behind_scenes": CommonPlayMediaType.BEHIND_THE_SCENES,
        "porn": CommonPlayMediaType.ADULT
    }

    def initialize(self):
        # TODO skill settings for these values
        self.gui_only = False  # not recommended
        self.audio_only = False
        self.use_mycroft_gui = False  # send all playback to the plugin
        self.compatibility_mode = True
        self.media_type_fallback = True  # if True send a Generic type query
        self.min_score = 30  # ignore matches with conf lower than this
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

        self.media_intents = IntentContainer()
        self.add_event("ovos.common_play.play", self.handle_play_request)
        self.register_media_intents()

        # TODO deezer creds
        email = "gavit58925@5sword.com"
        pswd = "jarbas666"
        self.deezer = deezeridu.Deezer(email=email, password=pswd)
        self.common_play.bind_deezer(self.deezer)

    def register_media_intents(self):
        """
        NOTE: uses the same format as mycroft .intent files, language
        support is handled the same way
        """
        locale_folder = join(dirname(__file__), "locale", self.lang)
        for intent_name in self.intent2media:
            path = join(locale_folder, intent_name + ".intent")
            if not isfile(path):
                continue
            with open(path) as intent:
                samples = intent.read().split("\n")
                for idx, s in enumerate(samples):
                    samples[idx] = s.replace("{{", "{").replace("}}", "}")
            LOG.debug(f"registering media type intent: {intent_name}")
            self.media_intents.add_intent(intent_name, samples)

    def classify_media(self, query):
        """ this method uses a strict regex based parser to determine what
        media type is being requested, this helps in the search process
        - only skills that support media type are considered
        - if no matches a generic search is performed
        - some skills only answer for specific media types, usually to avoid over matching
        - skills may use media type to calc confidence
        - skills may ignore media type

        NOTE: uses the same format as mycroft .intent files, language
        support is handled the same way
        """
        pred = self.media_intents.calc_intent(query)
        LOG.info(f"OVOSCommonPlay MediaType prediction: {pred}")
        LOG.debug(f"     utterance: {query}")
        intent = pred.get("name", "")
        if intent in self.intent2media:
            return self.intent2media[intent]
        LOG.debug("Generic OVOSCommonPlay query")
        return CommonPlayMediaType.GENERIC

    def stop(self, message=None):
        # will stop any playback in GUI and AudioService
        try:
            return self.common_play.stop()
        except:
            pass

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
    @intent_handler("play.intent")
    def handle_play_intent(self, message):
        utterance = message.data["utterance"]
        phrase = message.data.get("query", "")
        num = message.data.get("number", "")
        if num:
            phrase += " " + num

        # if media is currently paused, empty string means "resume playback"
        if self.should_resume(phrase):
            self.common_play.resume()
            return
        self.common_play.stop()
        self.speak_dialog("just.one.moment")

        # TODO searching UI page (?)
        self.enclosure.mouth_think()

        # reset common play playlist
        self.common_play.playlist = Playlist()

        # check if user said "play XXX audio only/no video"
        audio_only = self.audio_only
        if self.voc_match(phrase, "audio_only"):
            audio_only = True
            # dont include "audio only" in search query
            phrase = self.remove_voc(phrase, "audio_only")
            # dont include "audio only" in media type classification
            utterance = self.remove_voc(utterance, "audio_only").strip()

        # classify the query media type
        media_type = self.classify_media(utterance)

        # Now we place a query on the messsagebus for anyone who wants to
        # attempt to service a 'play.request' message.
        results = []
        phrase = phrase or utterance
        for r in self.common_play.search(phrase, media_type=media_type):
            results += r["results"]

        # ignore very low score matches
        results = [r for r in results
                   if r["match_confidence"] >= self.min_score]

        # filter deezer results if not logged in
        if not self.deezer:
            results = [r for r in results
                       if not is_deezer(r["uri"])]

        # check if user said "play XXX audio only"
        if audio_only:
            LOG.info("audio only requested, forcing audio playback "
                     "unconditionally")
            for idx, r in enumerate(results):
                # force streams to be played audio only
                results[idx]["playback"] = CommonPlayPlaybackType.AUDIO
        # filter video results if GUI not connected
        elif not can_use_gui(self.bus):
            LOG.info("unable to use GUI, filtering non-audio results")
            # filter video only streams
            results = [r for r in results
                       if r["playback"] == CommonPlayPlaybackType.AUDIO]

        if not results:
            self.speak_dialog("cant.play",
                              data={"phrase": phrase,
                                    "media_type": media_type})
            return

        best = self.select_best(results)

        self.common_play.play_media(best, results)

        self.enclosure.mouth_reset()  # TODO display music icon in mk1
        self.set_context("Playing")

    def should_resume(self, phrase):
        if self.common_play.playback_status == CommonPlayStatus.PAUSED:
            if not phrase.strip() or \
                    self.voc_match(phrase, "Resume", exact=True) or \
                    self.voc_match(phrase, "Play", exact=True):
                return True
        return False

    def select_best(self, results):
        # Look at any replies that arrived before the timeout
        # Find response(s) with the highest confidence
        best = None
        ties = []
        for handler in results:
            if not best or handler['match_confidence'] > best[
                'match_confidence']:
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
        LOG.debug(
            f"OVOSCommonPlay selected: {selected['skill_id']} - {selected['match_confidence']}")
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
