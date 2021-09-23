import random
from os.path import join, dirname, isfile

from adapt.intent import IntentBuilder
from mycroft.skills.core import intent_handler
from ovos_utils.gui import can_use_gui
from ovos_utils.log import LOG
from ovos_workshop.frameworks.playback import MediaType, \
    PlaybackType, OVOSCommonPlaybackInterface, CommonPlaySettings, PlayerState
from ovos_workshop.skills import OVOSSkill
from padacioso import IntentContainer


class BetterPlaybackControlSkill(OVOSSkill):
    intent2media = {
        "music": MediaType.MUSIC,
        "video": MediaType.VIDEO,
        "audiobook": MediaType.AUDIOBOOK,
        "radio": MediaType.RADIO,
        "radio_drama": MediaType.RADIO_THEATRE,
        "game": MediaType.GAME,
        "tv": MediaType.TV,
        "podcast": MediaType.PODCAST,
        "news": MediaType.NEWS,
        "movie": MediaType.MOVIE,
        "short_movie": MediaType.SHORT_FILM,
        "silent_movie": MediaType.SILENT_MOVIE,
        "bw_movie": MediaType.BLACK_WHITE_MOVIE,
        "documentaries": MediaType.DOCUMENTARY,
        "comic": MediaType.VISUAL_STORY,
        "movietrailer": MediaType.TRAILER,
        "behind_scenes": MediaType.BEHIND_THE_SCENES,
        "porn": MediaType.ADULT
    }

    def initialize(self):
        # TODO skill settings for these values
        self.settings["gui_only"] = False
        self.settings["audio_only"] = False
        self.settings["force_audioservice"] = False
        self.settings["backwards_compatibility"] = True
        self.settings["media_fallback"] = True
        self.settings["auto_play"] = True
        self.settings["max_timeout"] = 15
        self.settings["min_timeout"] = 8
        self.settings["min_score"] = 30
        cps_settings = CommonPlaySettings(
            backwards_compatibility=self.settings["backwards_compatibility"],
            media_fallback=self.settings["media_fallback"],
            max_timeout=self.settings["max_timeout"],
            min_timeout=self.settings["min_timeout"],
            autoplay=self.settings["auto_play"],
            force_audioservice=self.settings["force_audioservice"]
        )
        self.common_play = OVOSCommonPlaybackInterface(
            settings=cps_settings, bus=self.bus
        )
        self.media_intents = IntentContainer()
        self.register_media_intents()

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
        media type is being requested, this helps in the media process
        - only skills that support media type are considered
        - if no matches a generic media is performed
        - some skills only answer for specific media types, usually to avoid over matching
        - skills may use media type to calc confidence
        - skills may ignore media type

        NOTE: uses the same format as mycroft .intent files, language
        support is handled the same way
        """
        if self.voc_match(query, "audio_only"):
            query = self.remove_voc(query, "audio_only").strip()
        elif self.voc_match(query, "video_only"):
            query = self.remove_voc(query, "video_only")

        pred = self.media_intents.calc_intent(query)
        LOG.info(f"OVOSCommonPlay MediaType prediction: {pred}")
        LOG.debug(f"     utterance: {query}")
        intent = pred.get("name", "")
        if intent in self.intent2media:
            return self.intent2media[intent]
        LOG.debug("Generic OVOSCommonPlay query")
        return MediaType.GENERIC

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
        if self.common_play.player_state == PlayerState.PAUSED:
            self.common_play.resume()
        else:
            query = self.get_response("play.what")
            if query:
                message["utterance"] = query
                self.handle_play_intent(message)

    # playback selection
    @intent_handler("play.intent")
    def handle_play_intent(self, message):
        utterance = message.data["utterance"]
        phrase = message.data.get("query", "") or utterance
        num = message.data.get("number", "")
        if num:
            phrase += " " + num

        # if media is currently paused, empty string means "resume playback"
        if self.should_resume(phrase):
            self.common_play.resume()
            return
        if not phrase:
            phrase = self.get_response("play.what")
            if not phrase:
                # TODO some dialog ?
                self.stop()
                return

        self.common_play.reset()

        self.speak_dialog("just.one.moment")

        self.enclosure.mouth_think()

        # classify the query media type
        media_type = self.classify_media(utterance)
        # search common play skills
        results = self.search(phrase, utterance, media_type)

        if not results:
            self.speak_dialog("cant.play",
                              data={"phrase": phrase,
                                    "media_type": media_type})
        else:
            best = self.select_best(results)
            self.common_play.play_media(best, results)
            self.enclosure.mouth_reset()  # TODO display music icon in mk1
            self.set_context("Playing")

    def search(self, phrase, utterance, media_type):
        # check if user said "play XXX audio only/no video"
        audio_only = False
        video_only = False
        if self.voc_match(phrase, "audio_only"):
            audio_only = True
            # dont include "audio only" in search query
            phrase = self.remove_voc(phrase, "audio_only")
            # dont include "audio only" in media type classification
            utterance = self.remove_voc(utterance, "audio_only").strip()
        elif self.voc_match(phrase, "video_only"):
            video_only = True
            # dont include "video only" in search query
            phrase = self.remove_voc(phrase, "video_only")

        # Now we place a query on the messsagebus for anyone who wants to
        # attempt to service a 'play.request' message.
        results = []
        phrase = phrase or utterance
        for r in self.common_play.search(phrase, media_type=media_type):
            results += r["results"]

        # ignore very low score matches
        results = [r for r in results
                   if r["match_confidence"] >= self.settings["min_score"]]

        # check if user said "play XXX audio only"
        if audio_only:
            LOG.info("audio only requested, forcing audio playback "
                     "unconditionally")
            for idx, r in enumerate(results):
                # force streams to be played audio only
                results[idx]["playback"] = PlaybackType.AUDIO
        # check if user said "play XXX video only"
        elif video_only:
            LOG.info("video only requested, filtering non-video results")
            for idx, r in enumerate(results):
                if results[idx]["media_type"] == MediaType.VIDEO:
                    # force streams to be played in video mode, even if
                    # audio playback requested
                    results[idx]["playback"] = PlaybackType.VIDEO
            # filter audio only streams
            results = [r for r in results
                       if r["playback"] == PlaybackType.VIDEO]
        # filter video results if GUI not connected
        elif not can_use_gui(self.bus):
            LOG.info("unable to use GUI, filtering non-audio results")
            # filter video only streams
            results = [r for r in results
                       if r["playback"] == PlaybackType.AUDIO]
        return results

    def should_resume(self, phrase):
        if self.common_play.player_state == PlayerState.PAUSED:
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

            if self.settings["gui_only"]:
                # select only from VIDEO results if preference is set
                # WARNING this can effectively make it so that the same
                # skill is always selected
                gui_results = [r for r in ties if r["playback"] ==
                               PlaybackType.VIDEO]
                if len(gui_results):
                    selected = random.choice(gui_results)

            # TODO: Ask user to pick between ties or do it automagically
        else:
            selected = best
        LOG.debug(
            f"OVOSCommonPlay selected: {selected['skill_id']} - {selected['match_confidence']}")
        return selected

    def shutdown(self):
        self.common_play.shutdown()


def create_skill():
    return BetterPlaybackControlSkill()
