from ovos_utils.log import LOG
from ovos_workshop.skills import OVOSSkill


class OCPSkill(OVOSSkill):

    def initialize(self):
        LOG.info("This skill has been replaced with a plugin, "
                 "please see https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin")


def create_skill():
    return OCPSkill()
