"""Two optional caverns with persistent seals, enemies and treasure puzzles."""
import math
import pygame as pg
from enemies import Enemy


class CaveExpedition:
    WIDTH = 2200
    TITLES = ('푸른 결정의 동굴','무너진 빙붕의 동굴')

    def __init__(self, game, index):
        self.index = index
        cave = game.caves[index]
        self.state = cave.setdefault('expedition',{'stones':set(),'lever':False,'cleared':False,'defeated':set()})
        self.return_position = game.player.midbottom
        self.time = 0.0
        self.camera = 0.0
        self.invincible = 1.0
        self.hurt = 0.0
        self.right = True
        self.sliding = False
        self.notice = '봉인석 3개를 찾은 뒤 레버를 작동해 보물방을 여세요.'
        self.notice_left = 5.0
        self.pulses = []
        self.crumbles = {}
        if index == 0:
            ground = [(0,550,650,50),(720,550,520,50),(1320,550,880,50)]
            ledges = [(370,445,180,24),(570,345,170,24),(810,445,190,24),
                      (1100,345,170,24),(1340,445,170,24),(1540,345,190,24)]
            self.stones = [pg.Rect(590,315,24,30),pg.Rect(960,520,24,30),pg.Rect(1600,315,24,30)]
            self.arch = pg.Rect(865,450,120,62) # Ground-to-ceiling clearance: 38 px.
        else:
            ground = [(0,550,530,50),(640,550,460,50),(1390,550,810,50)]
            ledges = [(310,445,160,24),(540,425,160,24),(810,345,180,24),
                      (1100,445,110,24),(1240,445,110,24),(1460,445,150,24),(1670,345,180,24)]
            self.stones = [pg.Rect(340,415,24,30),pg.Rect(850,315,24,30),pg.Rect(1705,315,24,30)]
            self.arch = None
        self.grounds = [pg.Rect(*r) for r in ground]
        self.ledges = [pg.Rect(*r) for r in ledges]
        self.platforms = self.grounds+self.ledges
        self.fragile = {tuple(r) for r in self.ledges[3:5]} if index else set()
        self.lever = pg.Rect(1780,507,36,43)
        self.gate = pg.Rect(1880,0,30,550)
        self.chest = pg.Rect(2000,520,36,30)
        self.exit = pg.Rect(2100,460,70,90)
        patrols = [(self.grounds[1],80,'crab'),(self.ledges[-1],55,'spirit')]
        self.enemies = [(i,Enemy(platform,speed,kind)) for i,(platform,speed,kind) in enumerate(patrols)
                        if i not in self.state['defeated']]
        self.player = pg.Rect(55,498,40,52)
        self.reset_position()

    def say(self, text):
        self.notice,self.notice_left = text,3.0

    def reset_position(self):
        self.player.size = (40,52)
        self.player.midbottom = (80,550)
        self.x,self.y = map(float,self.player.topleft)
        self.vy = 0.0
        self.grounded = True
        self.sliding = False
        self.invincible = 2.0
        self.hurt = 0.0
        self.camera = 0.0

    def near(self, rect):
        return self.player.colliderect(rect.inflate(80,40))

    def action(self, game):
        if self.hurt:
            return
        if self.player.centerx<170:
            self.leave(game,False)
        elif self.near(self.lever):
            if len(self.state['stones'])<3:
                self.say(f"봉인석 {len(self.state['stones'])}/3 · 나머지 결정을 찾아오세요.")
            elif not self.state['lever']:
                self.state['lever'] = True
                self.pulses.append((self.lever.center,0.8))
                self.say('보물방의 봉인이 풀렸어요! 오른쪽 상자를 확인하세요.')
            else:
                self.say('보물방이 열려 있어요. 오른쪽으로 이동하세요.')
        elif self.state['lever'] and self.near(self.chest):
            if not game.caves[self.index]['treasure']:
                game.caves[self.index]['treasure'] = True
                game.score += 100
                self.pulses.append((self.chest.center,0.8))
                self.say('보물 발견! +100점 · 오른쪽 출구에서 E로 지름길 개방')
            else:
                self.say('이미 발견한 보물이에요. 오른쪽 출구로 나가세요.')
        elif self.near(self.exit) and game.caves[self.index]['treasure']:
            self.leave(game,True)
        else:
            self.say('입구 E 귀환 · 봉인석 3개 → 레버 E → 보물 상자 E')

    def leave(self, game, shortcut):
        if shortcut:
            platform = min(game.region_ledges[2 if self.index==0 else 4],key=lambda p:p.y)
            game.player.midbottom = (platform.left+28,platform.top)
            if not self.state['cleared']:
                self.state['cleared'] = True
                game.score += 150
                game.content.wallet += 3
                game.content.say('동굴 탐험 완료! +150점 · 먹이 +3 · 위쪽 지름길 개방')
            else:
                game.content.say('개방한 지름길로 돌아왔어요.')
        else:
            game.player.midbottom = self.return_position
            game.content.say('동굴 입구로 귀환! 봉인석과 보물 기록은 유지됩니다.')
        game.x,game.y = map(float,game.player.topleft)
        game.velocity_x = game.velocity_y = 0
        game.on_ground = True
        game.invincible = max(game.invincible,2)
        game.cave_expedition = None
        game.animation.reset()
        game.camera_x = max(0,min(game.world_width-800,game.player.centerx-400))
        game.update_presentation(0)

    def active_platforms(self):
        return [p for p in self.platforms if self.crumbles.get(tuple(p),(0,0))[1]<=0]

    def update(self, game, dt, direction, jump, slide):
        self.time += dt
        game.time += dt
        self.notice_left = max(0,self.notice_left-dt)
        self.invincible = max(0,self.invincible-dt)
        self.pulses = [(pos,life-dt) for pos,life in self.pulses if life>dt]
        if self.hurt:
            self.hurt = max(0,self.hurt-dt)
            if not self.hurt:
                self.reset_position()
            return
        for key,(elapsed,hidden) in list(self.crumbles.items()):
            if hidden:
                hidden = max(0,hidden-dt)
                if not hidden:
                    del self.crumbles[key]
                    continue
            else:
                elapsed += dt
                if elapsed>=0.8:
                    hidden = 4.0
            self.crumbles[key] = (elapsed,hidden)
        was_grounded,previous_x = self.grounded,self.player.x
        if direction:
            self.right = direction>0
        self.sliding = bool(slide and self.grounded and not jump)
        feet = self.player.midbottom
        standing = self.player.copy()
        standing.height = 52
        standing.midbottom = feet
        if self.arch and standing.colliderect(self.arch):
            self.sliding,jump = True,False
        self.player.height = 28 if self.sliding else 52
        self.player.midbottom = feet
        self.y = float(self.player.y)
        previous_bottom = self.player.bottom
        previous_top = self.player.top
        if jump and self.grounded:
            self.vy = -650
        self.x += direction*(365 if self.sliding else 270)*dt
        self.player.x = round(max(0,min(self.WIDTH-self.player.w,self.x)))
        obstacles = ([self.gate] if not self.state['lever'] else [])+([self.arch] if self.arch else [])
        for obstacle in obstacles:
            if self.player.colliderect(obstacle):
                if direction>0:
                    self.player.right = obstacle.left
                elif direction<0:
                    self.player.left = obstacle.right
        self.x = float(self.player.x)
        self.vy += 1800*dt
        self.y += self.vy*dt
        self.player.y = round(self.y)
        if self.arch and self.vy<0 and self.player.colliderect(self.arch) and previous_top>=self.arch.bottom:
            self.player.top = self.arch.bottom
            self.y = float(self.player.y)
            self.vy = 0
        self.grounded = False
        landings = self.active_platforms()+([self.arch] if self.arch else [])
        for platform in sorted(landings,key=lambda p:p.y):
            if self.vy>=0 and self.player.right>platform.left and self.player.left<platform.right and previous_bottom<=platform.top<=self.player.bottom:
                self.player.bottom = platform.top
                self.y = float(self.player.y)
                self.vy = 0
                self.grounded = True
                if tuple(platform) in self.fragile:
                    self.crumbles.setdefault(tuple(platform),(0,0))
                break
        if self.player.top>600:
            game.falls += 1
            self.reset_position()
            self.say('입구에서 다시 출발! 찾은 봉인석은 유지됩니다.')
            return
        for i,stone in enumerate(self.stones):
            if i not in self.state['stones'] and self.player.colliderect(stone):
                self.state['stones'].add(i)
                self.pulses.append((stone.center,0.8))
                self.say(f"봉인석 {len(self.state['stones'])}/3 · 세 개를 모으면 레버를 작동하세요.")
        for i,enemy in list(self.enemies):
            enemy.update(dt,self.player)
            if self.player.colliderect(enemy.rect):
                if self.vy>0 and previous_bottom<=enemy.previous_top+12:
                    self.enemies.remove((i,enemy))
                    self.state['defeated'].add(i)
                    game.score += enemy.points
                    self.vy = -400
                    self.pulses.append((enemy.rect.center,0.8))
                elif not self.invincible:
                    game.hits += 1
                    self.hurt = 0.35
                    self.say('피격! 입구로 돌아갑니다. 탐험 기록은 유지돼요.')
                    return
        target = max(0,min(self.WIDTH-800,self.player.centerx-400))
        self.camera += (target-self.camera)*(1-math.exp(-10*dt))
        game.animation.update(dt,self.player,self.vy,self.grounded,was_grounded,abs(self.player.x-previous_x))

    def draw(self, game, screen):
        # One continuous panorama covers the full scroll range without seams.
        drift = round(400*self.camera/(self.WIDTH-800))
        screen.blit(game.scene_backgrounds[2],(-drift,0))
        atmosphere = pg.Surface((800,600),pg.SRCALPHA)
        atmosphere.fill((8,27,50,55) if self.index==0 else (30,19,50,75))
        screen.blit(atmosphere,(0,0))
        # Distant translucent rock silhouettes stay behind the playable ledges.
        rocks = pg.Surface((800,600),pg.SRCALPHA)
        for layer in range(2):
            for i in range(16):
                x = round(i*205-self.camera*(0.18+layer*0.2))
                height = 20+(i*43+layer*21)%80
                color = (30+layer*10,69+layer*8,99+layer*9,45)
                pg.draw.polygon(rocks,color,[(x-25,85),(x+80,85),(x+35,85+height)])
                pg.draw.polygon(rocks,color,[(x-30,550),(x+120,550),(x+60,480-(i%3)*23)])
        screen.blit(rocks,(0,0))
        for i in range(35):
            x = round((i*137+self.time*6)%self.WIDTH-self.camera*0.65)
            y = 240+(i*67)%300
            pg.draw.circle(screen,(80,132,154),(x,y),1)
        pg.draw.rect(screen,(20,69,96),(0,550,800,50))
        for platform in self.active_platforms():
            rect = platform.move(-self.camera,0)
            kind = 'crumble' if tuple(platform) in self.fragile else 'ice'
            if tuple(platform) in self.crumbles:
                elapsed = self.crumbles[tuple(platform)][0]
                rect.move_ip(round(math.sin(elapsed*60)*elapsed*5),round(math.sin(elapsed*45)*elapsed*2))
            screen.blit(game.platform_texture(kind,platform.size),rect)
        game.art.grounded(screen,game.cave_image,(80-self.camera,550))
        if self.arch:
            arch = self.arch.move(-self.camera,0)
            # The low ceiling visibly matches the collider and leaves a slide gap.
            pg.draw.rect(screen,(50,110,143),arch,border_radius=8)
            pg.draw.rect(screen,(140,219,235),arch,2,border_radius=8)
            for x in range(arch.left+8,arch.right-5,20):
                pg.draw.polygon(screen,(155,227,244),[(x,arch.bottom-8),(x+10,arch.bottom-8),(x+5,arch.bottom)])
        for i,stone in enumerate(self.stones):
            if i in self.state['stones']:
                continue
            rect = stone.move(-self.camera,round(math.sin(self.time*2+i)*3))
            radius = 21+round(math.sin(self.time*3+i)*3)
            pg.draw.circle(screen,(34,87,113),rect.center,radius)
            pg.draw.polygon(screen,(128,229,246),[rect.midtop,rect.midright,rect.midbottom,rect.midleft])
            pg.draw.line(screen,'white',rect.midtop,(rect.centerx-4,rect.centery),2)
        game.art.place(screen,'lever-up' if self.state['lever'] else 'lever-down',self.lever.move(-self.camera,0).midbottom)
        if not self.state['lever']:
            gate = self.gate.move(-self.camera,0)
            for x in range(gate.left,gate.right,8):
                pg.draw.line(screen,(110,212,232),(x,gate.top),(x,gate.bottom),5)
            for i in range(3):
                pg.draw.circle(screen,(255,221,130) if i in self.state['stones'] else (63,111,143),(gate.centerx,250+i*33),6)
        if not game.caves[self.index]['treasure']:
            game.art.grounded(screen,game.chest_image,self.chest.move(-self.camera,0).midbottom)
        else:
            rect = self.chest.move(-self.camera,0)
            pg.draw.ellipse(screen,(118,202,180),(rect.left-8,rect.bottom-5,52,10),2)
        game.art.place(screen,'practice-arch',self.exit.move(-self.camera,0).midbottom)
        for _,enemy in self.enemies:
            enemy.draw(screen,self.camera,game.enemy_images)
        image = (game.animation.hurt_image(0.35-self.hurt,self.right) if self.hurt else
                 game.animation.action_image('slide',self.right) if self.sliding else game.animation.image(False,self.right))
        if self.hurt or not self.invincible or int(self.time*10)%2==0:
            rect = self.player.move(-self.camera,0)
            if self.hurt:
                rect.y -= round(math.sin((0.35-self.hurt)/0.35*math.pi)*14)
            screen.blit(image,image.get_rect(midbottom=rect.midbottom))
        for pos,life in self.pulses:
            center = (round(pos[0]-self.camera),pos[1])
            radius = round(12+(0.8-life)*60)
            pg.draw.circle(screen,(179,244,246),center,radius,2)
            for i in range(8):
                angle = i*math.pi/4+self.time
                dot = (round(center[0]+math.cos(angle)*radius),round(center[1]+math.sin(angle)*radius))
                pg.draw.circle(screen,(255,232,145),dot,max(1,round(life*4)))
        ui = game.ui
        ui.panel(screen,(12,12,776,73))
        ui.text(screen,self.TITLES[self.index],(28,23),ui.heading)
        ui.text(screen,'선택 탐험 · 입구에서 E로 언제든 귀환',(28,56),ui.small)
        ui.text(screen,f"봉인석 {len(self.state['stones'])}/3",(470,26),ui.heading)
        ui.text(screen,'보물 발견' if game.caves[self.index]['treasure'] else '보물방 열림' if self.state['lever'] else '보물방 봉인',(650,28),ui.body)
        ui.text(screen,f'{game.score} 점',(650,57),ui.small)
        message = self.notice if self.notice_left else ('E: 해안으로 귀환' if self.player.centerx<170 else
                  'E: 봉인 레버 작동' if self.near(self.lever) else
                  'E: 보물 상자 열기' if self.state['lever'] and self.near(self.chest) else
                  'E: 위쪽 지름길로 나가기' if self.near(self.exit) else '')
        if message:
            ui.panel(screen,(90,98,620,35),dark=True)
            ui.text(screen,message,(400,115),ui.small,'white',center=True,max_width=590)
        ui.panel(screen,(12,565,776,28))
        ui.text(screen,'← → 이동 · SPACE 점프 · ↓ 활주 · E 작동/귀환 · TAB 일지',(28,571),ui.small)
