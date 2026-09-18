"""Penguin sprite animation without altering the physics body."""
import math
import pygame as pg


class PenguinAnimation:
    def __init__(self, data):
        names = [f'walk-{i}' for i in range(1,9)] + ['idle', 'jump', 'fall', 'land']
        self.frames = {name: pg.image.load(str(data / f'penguin-animation-{name}.png')).convert_alpha()
                       for name in names}
        self.cache = {}
        for name, image in self.frames.items():
            for grown in (False, True):
                sized = pg.transform.scale(image, (96,84)) if grown else image
                for right in (False, True):
                    self.cache[name, grown, right] = pg.transform.flip(sized, True, False) if right else sized
        self.reset()

    def reset(self):
        self.state = 'idle'
        self.clock = 0.0
        self.distance = 0.0
        self.walk_clock = 0.0
        self.landing = 0.0
        self.puffs = []

    def update(self, dt, player, velocity_y, grounded, was_grounded, distance):
        self.clock += dt
        self.landing = max(0, self.landing-dt)
        self.puffs = [(x, y, life-dt) for x,y,life in self.puffs if life > dt]
        if grounded and not was_grounded:
            self.landing = 0.14
            self.puffs.extend((player.centerx+offset, player.bottom-2, 0.3) for offset in (-15,-7,7,15))
        if not grounded:
            self.state = 'jump' if velocity_y < 0 else 'fall'
        elif self.landing:
            self.state = 'land'
        elif distance > 0.2:
            self.state = 'walk'
            self.distance += abs(distance)
            # One cycle lasts about 0.95s normally, capped at 0.73s when boosted.
            rate = max(0.75, min(1.3, distance/max(dt, 0.001)/270))
            self.walk_clock += dt*rate
        else:
            self.state = 'idle'
            self.distance = 0
            self.walk_clock = 0

    def image(self, grown, right):
        name = f'walk-{int(self.walk_clock/0.12)%8+1}' if self.state == 'walk' else self.state
        image = self.cache[name, bool(grown), right]
        if self.state == 'idle':
            # Subtle breathing; the feet stay anchored on the platform.
            height = image.get_height()+round(math.sin(self.clock*2.8)*(1.5 if grown else 1))
            return pg.transform.scale(image, (image.get_width(), height))
        return image

    def draw_puffs(self, screen, camera_x):
        layer = pg.Surface(screen.get_size(), pg.SRCALPHA)
        for x,y,life in self.puffs:
            elapsed = 0.3-life
            drift = -1 if int(x)%2 else 1
            pos = (round(x-camera_x+drift*elapsed*24), round(y-elapsed*16))
            pg.draw.circle(layer, (225,249,255,round(190*life/0.3)), pos, max(1,round(4-life*6)))
        screen.blit(layer, (0,0))
