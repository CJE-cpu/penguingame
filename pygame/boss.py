"""Mid-game leopard seal boss with readable arcade-style attack phases."""
import math

import pygame as pg


class SealBoss:
    MAX_HITS = 3
    SCORE = 500

    def __init__(self, arena, floor_y, images):
        self.arena = pg.Rect(arena)
        self.floor_y = floor_y
        self.images = images
        self.rect = pg.Rect(0, 0, 136, 72)
        self.rect.midbottom = (self.arena.right-105, floor_y)
        self.x = float(self.rect.x)
        self.active = False
        self.defeated = False
        self.state = 'idle'
        self.timer = 0.0
        self.hits = 0
        self.direction = -1
        self.flash = 0.0
        self.shake = 0.0
        self.ammo = 0
        self.projectiles = []

    def start(self):
        if self.defeated or self.active:
            return False
        self.active = True
        self.state = 'roar'
        self.timer = 1.0
        return True

    def reset_encounter(self):
        if self.defeated:
            return
        self.active = False
        self.state = 'idle'
        self.timer = 0.0
        self.hits = 0
        self.direction = -1
        self.rect.midbottom = (self.arena.right-105, self.floor_y)
        self.x = float(self.rect.x)
        self.ammo = 0
        self.projectiles.clear()

    def restore_defeated(self, defeated):
        self.defeated = bool(defeated)
        if self.defeated:
            self.active = False
            self.state = 'defeated'
            self.timer = 0.0

    def update(self, dt, player):
        self.flash = max(0.0, self.flash-dt)
        self.shake = max(0.0, self.shake-dt)
        projectile_event = self.update_projectiles(dt)
        if projectile_event:
            return projectile_event
        if self.defeated:
            return None
        if not self.active:
            if self.arena.left+45 <= player.centerx <= self.arena.right:
                return 'start' if self.start() else None
            return None
        self.timer = max(0.0, self.timer-dt)
        if self.state == 'roar' and not self.timer:
            self.state = 'warning'
            self.timer = 0.85
            self.direction = -1 if player.centerx < self.rect.centerx else 1
        elif self.state == 'warning' and not self.timer:
            self.state = 'charge'
            self.timer = 1.8
        elif self.state == 'charge':
            self.x += self.direction*540*dt
            self.rect.x = round(self.x)
            left_wall = self.arena.left+18
            right_wall = self.arena.right-18
            impact = self.rect.left <= left_wall or self.rect.right >= right_wall
            if impact:
                if self.direction < 0:
                    self.rect.left = left_wall
                else:
                    self.rect.right = right_wall
                self.x = float(self.rect.x)
                self.state = 'stunned'
                self.timer = 1.9
                self.shake = 0.35
                self.ammo = min(2, self.ammo+1)
                return 'impact'
        elif self.state == 'charge' and not self.timer:
            self.state = 'stunned'
            self.timer = 1.2
        elif self.state == 'stunned' and not self.timer:
            self.state = 'roar'
            self.timer = max(0.42, 0.78-self.hits*0.12)
        return None

    def stomp(self):
        if self.state != 'stunned' or self.defeated:
            return False
        return self.take_hit()

    def take_hit(self):
        self.hits += 1
        self.flash = 0.32
        if self.hits >= self.MAX_HITS:
            self.defeated = True
            self.active = False
            self.state = 'defeated'
        else:
            self.state = 'roar'
            self.timer = 0.72
        return True

    def launch_ice(self, player, facing_right):
        if not self.active or self.defeated or self.ammo <= 0:
            return False
        self.ammo -= 1
        direction = 1 if facing_right else -1
        self.projectiles.append({
            'pos': pg.Vector2(player.centerx+direction*22, player.centery-8),
            'velocity': pg.Vector2(direction*560, -85),
            'life': 1.6,
        })
        return True

    def update_projectiles(self, dt):
        remaining = []
        for shot in self.projectiles:
            shot['life'] -= dt
            shot['velocity'].y += 240*dt
            shot['pos'] += shot['velocity']*dt
            rect = pg.Rect(0, 0, 22, 16)
            rect.center = (round(shot['pos'].x), round(shot['pos'].y))
            if (self.state == 'stunned' and not self.defeated
                    and rect.colliderect(self.weakspot())):
                self.take_hit()
                return 'ranged_defeat' if self.defeated else 'ranged_hit'
            if shot['life'] > 0 and self.arena.inflate(120, 220).colliderect(rect):
                remaining.append(shot)
        self.projectiles = remaining
        return None

    def weakspot(self):
        """Return the small head area that accepts a stomp while stunned."""
        width = 58
        height = 22
        center_x = self.rect.centerx + self.direction * 37
        return pg.Rect(center_x-width//2, self.rect.top-5, width, height)

    def can_stomp(self, player, previous_bottom, velocity_y):
        if self.state != 'stunned' or self.defeated or velocity_y <= 0:
            return False
        spot = self.weakspot()
        feet = pg.Rect(player.left+8, player.bottom-10,
                       max(1, player.width-16), 12)
        return feet.colliderect(spot) and previous_bottom <= spot.top+10

    def confine(self, player):
        if not self.active or self.defeated:
            return False
        changed = False
        if player.left < self.arena.left+12:
            player.left = self.arena.left+12
            changed = True
        if player.right > self.arena.right-12:
            player.right = self.arena.right-12
            changed = True
        return changed

    def image(self):
        name = self.state if self.state in self.images else 'idle'
        image = self.images[name]
        return pg.transform.flip(image, True, False) if self.direction > 0 else image

    def draw_terrain(self, screen, camera_x, time):
        """Draw a grounded arena that makes the charge lane easy to read."""
        left = self.arena.left-camera_x
        right = self.arena.right-camera_x
        if right < -40 or left > screen.get_width()+40:
            return
        floor = self.floor_y
        pg.draw.line(screen, (151, 211, 226), (left, floor-2),
                     (right, floor-2), 3)
        pg.draw.line(screen, (48, 105, 145), (left+18, floor+7),
                     (right-18, floor+7), 2)
        for index, world_x in enumerate(range(self.arena.left+62,
                                               self.arena.right-30, 91)):
            x = world_x-camera_x
            depth = 9+(index*7)%15
            pg.draw.lines(screen, (57, 108, 147), False,
                          [(x, floor), (x+7, floor+depth),
                           (x+2, floor+depth+7)], 2)
            if index % 2 == 0:
                pg.draw.line(screen, (127, 194, 213),
                             (x+7, floor+depth), (x+17, floor+depth-3), 1)
        for wall_x, direction in ((left, 1), (right, -1)):
            pg.draw.polygon(screen, (38, 84, 122),
                            [(wall_x, floor), (wall_x+direction*30, floor),
                             (wall_x+direction*20, floor-16),
                             (wall_x+direction*7, floor-28)])
            pg.draw.line(screen, (167, 226, 235),
                         (wall_x+direction*3, floor-25),
                         (wall_x+direction*22, floor-5), 2)

    def draw(self, screen, camera_x, time):
        if not self.active and not self.defeated:
            return
        offset = round(math.sin(time*70)*5*self.shake/0.35) if self.shake else 0
        rect = self.rect.move(-camera_x+offset, 0)
        if self.state == 'warning':
            pulse = 18+round(8*math.sin(time*16))
            pg.draw.ellipse(screen, (255, 111, 92),
                            (rect.centerx-pulse, rect.bottom-8, pulse*2, 12), 3)
            pg.draw.polygon(screen, (255, 220, 92),
                            [(rect.centerx, rect.top-23),
                             (rect.centerx-10, rect.top-5),
                             (rect.centerx+10, rect.top-5)])
        if self.active:
            for wall_x in (self.arena.left, self.arena.right):
                x = wall_x-camera_x
                for y in range(self.floor_y-116, self.floor_y, 22):
                    pg.draw.polygon(screen, (111, 222, 238),
                                    [(x, y-18), (x+10, y), (x, y+13), (x-10, y)])
                pg.draw.line(screen, (214, 251, 255),
                             (x, self.floor_y-126), (x, self.floor_y), 2)
        image = self.image()
        if self.flash and int(self.flash*30) % 2:
            white = pg.mask.from_surface(image, 40).to_surface(
                setcolor=(255, 255, 255, 230), unsetcolor=(0, 0, 0, 0))
            image = white
        screen.blit(image, image.get_rect(midbottom=rect.midbottom))
        if self.state == 'stunned' and self.active:
            spot = self.weakspot().move(-camera_x+offset, 0)
            pulse = 2 + round((math.sin(time*10)+1)*2)
            pg.draw.ellipse(screen, (255, 231, 112), spot.inflate(pulse, pulse), 2)
            pg.draw.ellipse(screen, (255, 255, 224), spot.inflate(-12, -8), 1)
        for shot in self.projectiles:
            x = round(shot['pos'].x-camera_x)
            y = round(shot['pos'].y)
            pg.draw.polygon(screen, (205, 247, 255),
                            [(x-11,y), (x-3,y-8), (x+11,y-3),
                             (x+7,y+7), (x-5,y+6)])
            pg.draw.line(screen, (91, 185, 217), (x-7,y+2), (x+6,y-3), 2)

    def draw_hud(self, game, screen):
        if not self.active or self.defeated:
            return
        ui = game.ui
        ui.panel(screen, (188, 88, 424, 58), dark=True)
        ui.text(screen, '빙벽의 우두머리 · 거대 바다표범', (400, 99),
                ui.body, 'white', center=True)
        objective = ('돌진을 피해서 빙벽 충돌을 유도하세요'
                     if self.state != 'stunned' else '지금 공격! 머리 밟기 또는 X 투척')
        ui.text(screen, objective, (400, 123), ui.small,
                (224, 247, 251), center=True, max_width=390)
        if self.ammo:
            ui.text(screen, f'얼음 조각 ×{self.ammo}', (275, 135), ui.small,
                    (255, 232, 137), center=True)
        for index in range(self.MAX_HITS):
            color = (255, 211, 91) if index < self.hits else (87, 135, 154)
            pg.draw.circle(screen, color, (545+index*21, 134), 6)

