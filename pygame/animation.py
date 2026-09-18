"""Penguin sprite animation without altering the physics body."""
import math
import pygame as pg
from art import atlas_cells, fit_cycle


class PenguinAnimation:
    def __init__(self, data):
        cells = atlas_cells(data/'adult-motion-atlas-v2.png',6,5)
        upright = fit_cycle(cells[:18],(64,56),padding=2)
        self.cycles = {'walk':upright[:8], 'idle':upright[8:10], 'jump':upright[10:12],
                       'fall':upright[12:14], 'land':upright[14:16], 'hurt':upright[16:18],
                       'slide':fit_cycle(cells[18:24],(80,34),padding=2),
                       'swim':fit_cycle(cells[24:30],(80,42),padding=2,anchor='center')}
        self.right_cycles = {name:[pg.transform.flip(f,True,False) for f in frames]
                             for name,frames in self.cycles.items()}
        self.frames = {f'walk-{i+1}':frame for i,frame in enumerate(self.cycles['walk'])}
        self.frames.update({name:self.cycles[name][0] for name in ('idle','jump','fall','land')})
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
        self.state_clock = 0.0
        self.puffs = []
        self.swim_clock = 0.0
        self.swim_angle = 0.0
        self.swim_movement = pg.Vector2()

    def update_swim(self, dt, movement, right):
        self.clock += dt
        self.swim_movement = pg.Vector2(movement)
        moving = self.swim_movement.length_squared()>0
        self.swim_clock += dt*(1 if moving else 0.35)
        target = -self.swim_movement.y*30*(1 if right else -1) if moving else 0
        self.swim_angle += (target-self.swim_angle)*(1-math.exp(-dt*10))

    def swim_image(self, right):
        frames = (self.right_cycles if right else self.cycles)['swim']
        image = frames[int(self.swim_clock/0.18)%len(frames)]
        return pg.transform.rotate(image,self.swim_angle)

    def swim_bob(self):
        return math.sin(self.clock*2.5)*(1.5 if self.swim_movement.length_squared() else 3)

    def update(self, dt, player, velocity_y, grounded, was_grounded, distance):
        old_state = self.state
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
        self.state_clock = self.state_clock+dt if self.state==old_state else 0.0

    def image(self, grown, right):
        frames = (self.right_cycles if right else self.cycles)[self.state]
        interval = 0.12 if self.state=='walk' else 0.6 if self.state=='idle' else 0.07 if self.state=='land' else 0.18
        clock = self.walk_clock if self.state=='walk' else self.clock if self.state=='idle' else self.state_clock
        index = int(clock/interval)%len(frames) if self.state in ('walk','idle') else min(len(frames)-1,int(clock/interval))
        image = frames[index]
        return pg.transform.scale(image,(96,84)) if grown else image

    def action_image(self, action, right):
        frames = (self.right_cycles if right else self.cycles)[action]
        interval = 0.14 if action=='swim' else 0.16
        return frames[int(self.clock/interval)%len(frames)]

    def hurt_image(self, age, right):
        frames = (self.right_cycles if right else self.cycles)['hurt']
        return frames[min(1,int(age/0.16))]

    def draw_puffs(self, screen, camera_x):
        layer = pg.Surface(screen.get_size(), pg.SRCALPHA)
        for x,y,life in self.puffs:
            elapsed = 0.3-life
            drift = -1 if int(x)%2 else 1
            pos = (round(x-camera_x+drift*elapsed*24), round(y-elapsed*16))
            pg.draw.circle(layer, (225,249,255,round(190*life/0.3)), pos, max(1,round(4-life*6)))
        screen.blit(layer, (0,0))
