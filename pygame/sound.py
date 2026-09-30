"""Small, failure-safe audio layer shared by desktop and browser builds."""
from pathlib import Path

import pygame as pg


class GameAudio:
    EFFECT_VOLUME = 0.42
    AMBIENT_VOLUME = 0.11
    REGION_TRACKS = ('coast', 'glacier', 'ice-cave', 'blizzard',
                     'fractured', 'sunset')
    _sounds = {}

    def __init__(self, data_path):
        self.audio_path = Path(data_path) / 'audio'
        self.enabled = True
        self.available = None
        self.current_track = None
        self.ambient_channel = None

    def _ready(self):
        if self.available is False:
            return False
        try:
            if not pg.mixer.get_init():
                pg.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            pg.mixer.set_num_channels(max(8, pg.mixer.get_num_channels()))
            self.available = True
        except (pg.error, OSError):
            self.available = False
        return bool(self.available)

    def _sound(self, filename):
        path = str(self.audio_path / filename)
        sound = self._sounds.get(path)
        if sound is None:
            sound = pg.mixer.Sound(path)
            self._sounds[path] = sound
        return sound

    def play(self, name):
        if not self.enabled or not self._ready():
            return
        try:
            sound = self._sound(name + '.ogg')
            sound.set_volume(self.EFFECT_VOLUME)
            sound.play()
        except (pg.error, OSError):
            self.available = False

    def set_scene(self, region, underwater=False):
        track = 'underwater' if underwater else self.REGION_TRACKS[
            max(0, min(len(self.REGION_TRACKS)-1, int(region)))]
        if track == self.current_track:
            return
        self.current_track = track
        if not self.enabled or not self._ready():
            return
        try:
            if self.ambient_channel:
                self.ambient_channel.fadeout(350)
            sound = self._sound('ambient-' + track + '.ogg')
            sound.set_volume(self.AMBIENT_VOLUME)
            self.ambient_channel = sound.play(loops=-1, fade_ms=350)
        except (pg.error, OSError):
            self.available = False

    def toggle(self):
        self.enabled = not self.enabled
        if not self.enabled:
            if self.ambient_channel:
                self.ambient_channel.fadeout(180)
            pg.mixer.stop() if pg.mixer.get_init() else None
        else:
            previous = self.current_track
            self.current_track = None
            if previous:
                if previous == 'underwater':
                    self.set_scene(0, underwater=True)
                else:
                    self.set_scene(self.REGION_TRACKS.index(previous))
        return self.enabled

