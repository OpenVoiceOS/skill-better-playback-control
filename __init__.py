from ovos_utils.log import LOG
from ovos_workshop.skills import OVOSSkill


class OCPSkill(OVOSSkill):

    def initialize(self):
        # TODO setup the plugin in mycroft.conf if needed
        # allows distributing OCP via skill stores
        LOG.info("This skill has been replaced with a plugin, "
                 "please see https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin")


def create_skill():
    return OCPSkill()
