#!/usr/bin/env python3
from setuptools import setup

# skill_id=package_name:SkillClass
PLUGIN_ENTRY_POINT = 'mycroft-playback-control.mycroftai=ovos_skill_common_play:OCPSkill'
# in this case the skill_id is defined to purposefully replace the mycroft version of the skill,
# or rather to be replaced by it in case it is present. all skill directories take precedence over plugin skills


setup(
    # this is the package name that goes on pip
    name='ovos-skill-common-play',
    version='0.0.1',
    description='OVOS common-play skill plugin',
    url='https://github.com/OpenVoiceOS/skill-ovos-common-play',
    author='JarbasAi',
    author_email='jarbasai@mailfence.com',
    license='Apache-2.0',
    package_dir={"ovos_skill_common_play": ""},
    packages=['ovos_skill_common_play'],
    include_package_data=True,
    install_requires=["ovos_plugin_common_play>=0.0.1a2"],
    keywords='ovos skill plugin',
    entry_points={'ovos.plugin.skill': PLUGIN_ENTRY_POINT}
)
