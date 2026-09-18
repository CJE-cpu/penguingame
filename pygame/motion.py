"""Short combat poses and a companion following the player's recorded route."""
from collections import deque
import math
import pygame as pg


class CombatMotion:
    def __init__(self):
        self.reset()

    def reset(self):
        self.defeated = []
        self.hurt = 0.0
        self.kick = 0.0
        self.hit_direction = 1

    def defeat(self, enemy, images):
        frames = images[enemy.kind]
        index = int(enemy.clock*5)%2 if enemy.kind == 'skua' else int(bool(enemy.charge or enemy.warning)) if enemy.kind == 'seal' else int(enemy.rect.y < enemy.base_y)
        image = frames[min(index, len(frames)-1)]
        if enemy.speed > 0:
            image = pg.transform.flip(image, True, False)
        self.defeated.append((enemy.rect.center, image.copy(), 0.0, 1 if enemy.speed > 0 else -1))
        self.kick = 0.25

    def hit(self, player, enemy):
        self.hurt = 0.45
        self.hit_direction = -1 if player.centerx < enemy.rect.centerx else 1

    def update(self, dt):
        self.hurt = max(0, self.hurt-dt)
        self.kick = max(0, self.kick-dt)
        self.defeated = [(p, image, age+dt, direction) for p, image, age, direction in self.defeated if age+dt < 0.75]

    def pose(self, image):
        if self.hurt:
            age = 0.45-self.hurt
            image = image.copy()
            if int(age*24)%2 == 0:
                image.fill((255, 110, 110, 255), special_flags=pg.BLEND_RGBA_MULT)
            return pg.transform.rotate(image, self.hit_direction*(15+20*math.sin(age*9)))
        if self.kick:
            pulse = math.sin(self.kick/0.25*math.pi)
            return pg.transform.scale(image, (round(image.get_width()*(1+0.15*pulse)), round(image.get_height()*(1-0.15*pulse))))
        return image

    def draw(self, game, screen):
        for pos, image, age, direction in self.defeated:
            if age < 0.12:
                image = pg.transform.scale(image, (round(image.get_width()*1.3), max(1, round(image.get_height()*0.55))))
            else:
                image = pg.transform.rotate(image, direction*(age-0.12)*420)
            image.set_alpha(round(255*min(1, (0.75-age)/0.3)))
            x = pos[0]-game.camera_x+direction*age*70
            y = pos[1]-math.sin(age/0.75*math.pi)*55+age*30
            screen.blit(image, image.get_rect(center=(round(x), round(y))))
        if self.hurt:
            cx = round(game.player.centerx-game.camera_x)
            for i in range(3):
                phase = game.time*10+i*math.tau/3
                x, y = round(cx+math.cos(phase)*25), round(game.player.top-12+math.sin(phase)*7)
                pg.draw.line(screen, (255, 220, 100), (x-4,y), (x+4,y), 3)
                pg.draw.line(screen, (255, 245, 165), (x,y-4), (x,y+4), 3)


class BabyCompanion:
    def __init__(self):
        self.reset()

    def reset(self):
        self.route = deque()
        self.pos = None
        self.facing_right = False
        self.walk_clock = 0.0
        self.moving = False
        self.airborne = False

    def start(self, game, baby):
        self.reset()
        self.pos = tuple(map(float, baby['rect'].midbottom))
        self.route.append((game.time, game.player.midbottom, game.on_ground))

    def update(self, game, dt):
        if game.carried_baby is None:
            self.reset()
            return
        if self.pos is None:
            self.start(game, game.babies[game.carried_baby])
        if not self.route or self.route[-1][1] != game.player.midbottom or self.route[-1][2] != game.on_ground:
            self.route.append((game.time, game.player.midbottom, game.on_ground))
        while (len(self.route)>1 and self.route[1][0] <= game.time-0.23
               and (math.dist(self.route[1][1], game.player.midbottom) >= 36 or not self.route[0][2])):
            self.route.popleft()
        _, target, grounded = self.route[0]
        previous = self.pos
        # Delayed footsteps replay jumps and landings rather than crossing gaps.
        self.pos = tuple(map(float, target))
        if grounded and game.on_ground and math.dist(self.pos, game.player.midbottom) < 36:
            supports = [p for p in game.active_platforms() if p.top == target[1] and p.left <= target[0] <= p.right]
            if supports:
                support = supports[0]
                desired = game.player.centerx + (-40 if game.facing_right else 40)
                desired = max(support.left+16, min(support.right-16, desired))
                step = max(-180*dt, min(180*dt, desired-previous[0]))
                self.pos = (previous[0]+step, float(target[1]))
        dx = self.pos[0]-previous[0]
        self.moving = abs(dx)>0.1
        if self.moving:
            self.facing_right = dx > 0
            self.walk_clock += dt
        self.airborne = not grounded

    def draw(self, game, screen):
        if game.carried_baby is None or self.pos is None:
            return
        image = game.baby_image
        if self.facing_right:
            image = pg.transform.flip(image, True, False)
        if self.airborne:
            image = pg.transform.scale(image, (35, 36))
        elif self.moving:
            image = pg.transform.rotate(image, math.sin(self.walk_clock*17)*9)
        x, y = self.pos
        screen.blit(image, image.get_rect(midbottom=(round(x-game.camera_x), round(y))))
