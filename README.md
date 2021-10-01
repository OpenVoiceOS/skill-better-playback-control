# <img src='https://raw.githack.com/FortAwesome/Font-Awesome/master/svgs/solid/play.svg' card_color='#22a7f0' width='50' height='50' style='vertical-align:bottom'/> OVOS Common Playback

This skill has been replaced with a plugin, it doesn't do anything by itself except installing the plugin

Please see https://github.com/OpenVoiceOS/ovos-ocp-audio-plugin

To enable OCP edit mycroft.conf

```json
{
  "Audio": {
    "backends": {
      "local": {
        "type": "ovos_common_play",
        "active": true
      },
      "vlc": {
        "type": "ovos_vlc",
        "active": true
      }
    },
    "default-backend": "local"
  }
}
```
