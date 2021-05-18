# <img src='https://raw.githack.com/FortAwesome/Font-Awesome/master/svgs/solid/play.svg' card_color='#22a7f0' width='50' height='50' style='vertical-align:bottom'/> Better Playback Control
Better Common playback control system

NOTE: this is meant a better alternative to the official playback control skill, it will be blacklisted

## About
This Skill doesn't do anything by itself, but it provides an important common
language for audio playback skills.  By handling simple phrases like
'pause', this one Skill can turn around and rebroadcast the [messagebus](https://mycroft.ai/documentation/message-bus/)
command `mycroft.audio.service.pause`, allowing several music services to share
common terminology such as "pause".

Additionally, this implements the common Play handler.  This allows playback
services to negotiate which is best suited to play back a specific request.

What's New??
- Track Status - [skill-playback-control/pull/35](https://github.com/MycroftAI/skill-playback-control/pull/35)
    - better handling of playback status, see [MycroftAI/mycroft-core#2619](https://github.com/MycroftAI/mycroft-core/pull/2619) and [MycroftAI/mycroft-core#2674](https://github.com/MycroftAI/mycroft-core/pull/2674)
- MatchType - [skill-playback-control/pull/32](https://github.com/MycroftAI/skill-playback-control/pull/32) and [mycroft-core/pull/2660](https://github.com/MycroftAI/mycroft-core/pull/2660)
    - playback now has a "media type" see [mycroft-core/issues/2658](https://github.com/MycroftAI/mycroft-core/issues/2658)
    - depending on intent additional info is used to help playback selection
    - integrates with video / media skills, no longer focused on music only
- Resume - [skill-playback-control/pull/38](https://github.com/MycroftAI/skill-playback-control/pull/38)
    - When told to "play" if music is paused now it restarts see [skill-playback-control/issues/18](https://github.com/MycroftAI/skill-playback-control/issues/18)
- Timeout - [skill-playback-control/pull/33](https://github.com/MycroftAI/skill-playback-control/pull/33)
    - improves the common play framework handling, timeout is now configurable,
      default is 5 seconds, previoulsy many skills failed to play because 
      the timeout was too small


## Examples
* "Play my summer playlist"
* "Play Pandora"
* "Pause"
* "Resume"
* "Next song"
* "Next track"
* "Previous track"
* "Previous song"
* "Play NASA TV channel"
* "Play Soma FM internet radio"
* "Play a cat video"
* "Play This Week in Tech podcast"
* "Play Portuguese News"
* "Play music the gods made heavy metal"
* "Play a horror movie"
* "Play a lovecraft audiobook"
* "Play dagon lovecraft visual comic"
* "Play game Planet Fall"
* "Play trailer for The Land Before Time"
* "Play {your favorite category} porn"

# Platform support

- :heavy_check_mark: - tested and confirmed working
- :x: - incompatible/non-functional
- :question: - untested
- :construction: - partial support

|     platform    |   status   |  tag  | version | last tested | 
|:---------------:|:----------:|:-----:|:-------:|:-----------:|
|    [Chatterbox](https://hellochatterbox.com)   | :question: |  dev  |         |    never    | 
|     [HolmesV](https://github.com/HelloChatterbox/HolmesV)     | :question: |  dev  |         |    never    | 
|    [LocalHive](https://github.com/JarbasHiveMind/LocalHive)    | :question: |  dev  |         |    never    |  
|  [Mycroft Mark1](https://github.com/MycroftAI/enclosure-mark1)    | :question: |  dev  |         |    never    | 
|  [Mycroft Mark2](https://github.com/MycroftAI/hardware-mycroft-mark-II)    | :question: |  dev  |         |    never    |  
|    [NeonGecko](https://neon.ai)      | :question: |  dev  |         |    never    |   
|       [OVOS](https://github.com/OpenVoiceOS)        | :question: |  dev  |         |    never    |    
|     [Picroft](https://github.com/MycroftAI/enclosure-picroft)       | :question: |  dev  |         |    never    |  
| [Plasma Bigscreen](https://plasma-bigscreen.org/)  | :question: |  dev  |         |    never    |  

- `tag` - link to github release / branch / commit
- `version` - link to release/commit of platform repo where this was tested

## Credits
Mycroft AI (@MycroftAI)
Jarbas AI

## Category
**Media**

## Tags
#movies
#audiobooks
#podcasts
#games
#video
#media
#music
#play
#playback
#pause
#resume
#next
#system
