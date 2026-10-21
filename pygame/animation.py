"""Penguin sprite animation without altering the physics body."""
import math
import pygame as pg
from art import atlas_cells, fit_cycle


class PenguinAnimation:
    def __init__(self, data):
        self.puff_layer = pg.Surface((800, 600), pg.SRCALPHA)
        cells = atlas_cells(data/'adult-motion-atlas-v2.png',6,5)
        upright = fit_cycle(cells[:18],(64,56),padding=2)
        self.cycles = {'walk':upright[:8], 'idle':upright[8:10], 'jump':upright[10:12],
                        'fall':upright[12:14], 'land':upright[14:16], 'hurt':upright[16:18],
                        'slide':fit_cycle(cells[18:24],(80,34),padding=2),
                        'swim':fit_cycle(cells[24:30],(80,42),padding=2,anchor='center')}
        self.right_cycles = {name:[pg.transform.flip(f,True,False) for f in frames]
                              for name,frames in self.cycles.items()}
        self.grown_cycles = {
            False: {name: [pg.transform.scale(frame, (96, 84)) for frame in frames]
                    for name, frames in self.cycles.items()},
            True: {name: [pg.transform.scale(frame, (96, 84)) for frame in frames]
                    for name, frames in self.right_cycles.items()},
        }
        self.frames = {f'walk-{i+1}':frame for i,frame in enumerate(self.cycles['walk'])}
        self.frames.update({name:self.cycles[name][0] for name in ('idle','jump','fall','land')})
        self.cache = {}
        self.swim_rotation_cache = {}
        self.pose_cache = {}
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
        index = int(self.swim_clock/0.18)%len(frames)
        angle = round(self.swim_angle/3)*3
        key = (right, index, angle)
        if key not in self.swim_rotation_cache:
            self.swim_rotation_cache[key] = pg.transform.rotate(frames[index], angle)
        return self.swim_rotation_cache[key]

    def swim_bob(self):
        return math.sin(self.clock*2.5)*(1.5 if self.swim_movement.length_squared() else 3)

    def _state_timing(self, state):
        if state == 'walk':
            return 0.12
        if state == 'idle':
            return 0.28
        if state == 'land':
            return 0.08
        if state == 'hurt':
            return 0.16
        return 0.18

    def _state_pose(self, state, moving, velocity_y):
        if state == 'idle':
            bob = math.sin(self.clock * 2.6) * 1.4
            return (1.0, 1.0 + bob * 0.02, 1.0)
        if state == 'walk':
            stride = math.sin(self.walk_clock * 11.0)
            return (1.0 + abs(stride) * 0.08, 1.0 - abs(stride) * 0.08, 0.95 + stride * 0.04)
        if state == 'jump':
            stretch = max(0.0, -velocity_y) / 700.0
            return (0.96 - stretch * 0.08, 1.12 + stretch * 0.14, 1.0)
        if state == 'fall':
            stretch = max(0.0, velocity_y) / 850.0
            return (1.06 + stretch * 0.04, 0.9 - stretch * 0.1, 1.0)
        if state == 'land':
            return (1.04, 0.88, 1.0)
        if state == 'hurt':
            return (1.0, 1.0, 1.0)
        if state == 'slide':
            return (1.12, 0.76, 1.0)
        return (1.0, 1.0, 1.0)

    def _transform_frame(self, frame, state, grown, right, moving=False, velocity_y=0.0):
        key = (state, grown, right, frame.get_size(), moving, round(velocity_y, 2))
        if key in self.pose_cache:
            return self.pose_cache[key]

        sx, sy, sway = self._state_pose(state, moving, velocity_y)
        width = max(1, round(frame.get_width() * sx))
        height = max(1, round(frame.get_height() * sy))
        scaled = pg.transform.smoothscale(frame, (width, height))
        if sway != 1.0 and grown:
            tilt = sway * 5.0
            scaled = pg.transform.rotate(scaled, tilt if right else -tilt)
        if right:
            scaled = pg.transform.flip(scaled, True, False)
        self.pose_cache[key] = scaled
        if len(self.pose_cache) > 256:
            self.pose_cache.clear()
        return scaled

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
            rate = max(0.75, min(1.3, distance/max(dt, 0.001)/270))
            self.walk_clock += dt*rate
        else:
            self.state = 'idle'
            self.distance = 0
            self.walk_clock = 0
        self.state_clock = self.state_clock+dt if self.state==old_state else 0.0

    def image(self, grown, right):
        frames = (self.right_cycles if right else self.cycles)[self.state]
        interval = self._state_timing(self.state)
        if self.state in ('walk', 'idle'):
            clock = self.walk_clock if self.state == 'walk' else self.clock
            index = int(clock/interval) % len(frames)
        else:
            clock = self.state_clock if self.state == 'land' else self.clock
            index = min(len(frames)-1, int(clock/interval))
        base = frames[index]
        moving = self.state == 'walk' and abs(self.distance) > 0.1
        frame = self._transform_frame(base, self.state, grown, right, moving=moving, velocity_y=self.clock)
        return frame

    def action_image(self, action, right):
        frames = (self.right_cycles if right else self.cycles)[action]
        interval = 0.14 if action=='swim' else 0.16
        index = int(self.clock/interval) % len(frames)
        base = frames[index]
        return self._transform_frame(base, action, False, right, moving=action=='swim', velocity_y=0.0)

    def hurt_image(self, age, right):
        frames = (self.right_cycles if right else self.cycles)['hurt']
        index = min(len(frames)-1, int(age/0.16))
        return self._transform_frame(frames[index], 'hurt', False, right, velocity_y=0.0)

    def draw_puffs(self, screen, camera_x):
        if not self.puffs:
            return
        layer = self.puff_layer
        layer.fill((0, 0, 0, 0))
        for x,y,life in self.puffs:
            elapsed = 0.3-life
            drift = -1 if int(x)%2 else 1
            pos = (round(x-camera_x+drift*elapsed*24), round(y-elapsed*16))
            alpha = round(200 * (life / 0.3))
            radius = max(1, round(4 - life * 6))
            pg.draw.circle(layer, (225,249,255,alpha), pos, radius)
            pg.draw.circle(layer, (255,255,255,alpha//2), pos, max(1, radius-1))
        screen.blit(layer, (0,0))

