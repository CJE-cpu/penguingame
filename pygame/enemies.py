"""Antarctic patrol, charge, flying and hopping enemies."""
import math
import pygame as pg

ENEMY_INFO = {'crab': ('게', (44,30), 30), 'seal': ('물범', (68,34), 40),
              'skua': ('도둑갈매기', (48,40), 45), 'spirit': ('얼음 정령', (36,40), 50)}


class Enemy:
    def __init__(self, platform, speed, kind='crab'):
        self.kind = kind
        _, size, self.points = ENEMY_INFO[kind]
        self.rect = pg.Rect((0,0), size)
        self.rect.midbottom = (platform.centerx, platform.top)
        self.x = float(self.rect.x)
        self.left, self.right = platform.left+8, platform.right-8
        self.speed = speed
        self.patrol_speed = abs(speed)
        self.clock = 0.0
        self.base_y = self.rect.y-(140 if kind == 'skua' else 0)
        self.y = float(self.base_y)
        self.rect.y = self.base_y
        self.previous_top = self.rect.top
        self.velocity_y = 0.0
        self.cooldown = 1.0
        self.warning = 0.0
        self.charge = 0.0

    def update(self, dt, player=None):
        self.previous_top = self.rect.top
        self.clock += dt
        self.cooldown = max(0,self.cooldown-dt)
        move_speed = self.speed
        if self.kind == 'seal':
            if self.warning:
                self.warning = max(0,self.warning-dt)
                move_speed = 0
                if not self.warning:
                    self.charge = 0.45
            elif self.charge:
                self.charge = max(0,self.charge-dt)
                move_speed = math.copysign(230,self.speed)
                if not self.charge:
                    self.cooldown = 2.0
            elif (player is not None and not self.cooldown
                  and abs(player.centerx-self.rect.centerx)<210
                  and abs(player.centery-self.rect.centery)<70):
                self.speed = math.copysign(self.patrol_speed,player.centerx-self.rect.centerx)
                self.warning = 0.55
                move_speed = 0
        self.x += move_speed*dt
        if self.x <= self.left:
            self.x = float(self.left)
            self.speed = abs(self.speed)
        elif self.x >= self.right-self.rect.width:
            self.x = float(self.right-self.rect.width)
            self.speed = -abs(self.speed)
        self.rect.x = round(self.x)
        if self.kind == 'skua':
            self.rect.y = round(self.base_y+math.sin(self.clock*2.3)*28)
        elif self.kind == 'spirit':
            if not self.cooldown and self.y >= self.base_y:
                self.velocity_y = -290
                self.cooldown = 1.6
            self.velocity_y += 950*dt
            self.y = min(self.base_y,self.y+self.velocity_y*dt)
            if self.y == self.base_y:
                self.velocity_y = 0
            self.rect.y = round(self.y)

    def sprite_image(self, images):
        if self.kind == 'seal':
            index = 3 if self.charge else 2 if self.warning else int(self.clock/0.2)%2
        elif self.kind == 'spirit':
            index = (2 if self.velocity_y<0 else 3) if self.rect.y<self.base_y else int(self.clock/0.3)%2
        else:
            index = int(self.clock/(0.16 if self.kind=='skua' else 0.2))%4
        frames = images[self.kind]
        image = frames[min(index,len(frames)-1)]
        if self.speed > 0:
            image = pg.transform.flip(image,True,False)
        return image

    def draw(self, screen, camera_x, images):
        image = self.sprite_image(images)
        rect = self.rect.move(-camera_x,0)
        screen.blit(image,rect)
        if self.warning:
            pg.draw.polygon(screen,(255,209,90), [(rect.centerx,rect.y-19),(rect.centerx-7,rect.y-5),(rect.centerx+7,rect.y-5)])
            pg.draw.line(screen,(99,61,30),(rect.centerx,rect.y-15),(rect.centerx,rect.y-10),2)
