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
        self.stone_boost = 0.0
        self.right = True
        self.sliding = False
        self.notice = '봉인석 3개를 찾은 뒤 레버를 작동해 보물방을 여세요.'
        self.notice_left = 5.0
        self.pulses = []
        self.crumbles = {}
        self.texture_cache = {}
        self.entrance_image = pg.transform.smoothscale(game.cave_image, (150, 112))
        self.entrance_image.set_alpha(178)
        self.arch_image = None
        self.atmosphere_layer = pg.Surface((800, 600), pg.SRCALPHA)
        self.mist_layer = pg.Surface((800, 92), pg.SRCALPHA)
        self.background = game.cave_backgrounds[index]
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
        for platform_index, platform in enumerate(self.platforms):
            if any(platform.colliderect(other)
                   for other in self.platforms[platform_index+1:]):
                raise ValueError('Cave platforms must not overlap')
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
        self.jump_hold = 0.0
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
                game.audio.play('rescue')
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
            game.player.midbottom = (platform.centerx,platform.top)
            if not self.state['cleared']:
                self.state['cleared'] = True
                game.score += 150
                game.content.wallet += 3
                game.content.say('동굴 탐험 완료! +150점 · 먹이 +3 · 위쪽 지름길 개방')
            else:
                game.content.say('개방한 지름길로 돌아왔어요.')
        else:
            region = 2 if self.index == 0 else 4
            entrance = game.caves[self.index]['rect']
            supports = [ground for ground in game.region_grounds[region]
                        if ground.left <= entrance.centerx <= ground.right]
            platform = min(supports, key=lambda ground: abs(ground.top-entrance.bottom))
            # Stay within interaction range for an immediate re-entry while
            # leaving ample ground between the player and the outer cliff.
            safe_x = max(platform.left+90,
                         min(platform.right-90, entrance.left-10))
            game.player.midbottom = (safe_x, platform.top)
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

    def platform_texture(self, size, fragile=False, ground=False):
        key = (size, fragile, ground, self.index)
        if key in self.texture_cache:
            return self.texture_cache[key]
        width, height = size
        surface = pg.Surface(size, pg.SRCALPHA)
        if self.index == 0:
            deep, middle, edge, shine = ((18,58,82), (35,91,119),
                                         (105,190,211), (190,242,248))
        else:
            deep, middle, edge, shine = ((42,38,70), (70,65,108),
                                         (126,140,190), (207,224,250))
        if ground:
            surface.fill(middle)
            pg.draw.rect(surface, deep, (0, min(24, height), width,
                                         max(0, height-24)))
        else:
            pg.draw.polygon(surface, middle,
                            [(0, 7), (width, 7), (width-8, height-1),
                             (8, height-1)])
            pg.draw.line(surface, deep, (8, height-2), (width-9, height-2), 2)
        # A single clean cap separates walkable terrain from the background.
        pg.draw.rect(surface, edge, (0, 0, width, min(10, height)))
        pg.draw.line(surface, shine, (1, 2), (width-2, 2), 2)
        # Long blocks receive only one subdued natural seam.
        if width >= 170 and height >= 22:
            seam_x = width // 2 + (-13 if self.index else 11)
            pg.draw.lines(surface, (*edge, 150), False,
                          [(seam_x, 11), (seam_x-5, 17),
                           (seam_x+2, min(height-2, 26))], 1)
        if fragile:
            for x in (width//3, width*2//3):
                pg.draw.line(surface, (239,159,184), (x, 1), (x-8, 11), 2)
                pg.draw.line(surface, (239,159,184), (x-8, 11), (x+5, 20), 2)
        self.texture_cache[key] = surface
        return surface

    def update(self, game, dt, direction, jump, slide, jump_held=None):
        self.time += dt
        game.time += dt
        self.notice_left = max(0,self.notice_left-dt)
        self.stone_boost = max(0.0, self.stone_boost-dt)
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
            self.grounded = False
            self.jump_hold = 0.22
            game.audio.play('jump')
        if self.vy < 0 and self.jump_hold > 0:
            if jump_held is True:
                self.vy -= 1050*dt
                self.jump_hold = max(0.0,self.jump_hold-dt)
            elif jump_held is False:
                self.vy = max(self.vy,-390)
                self.jump_hold = 0.0
        move_speed = 330 if self.stone_boost else 270
        self.x += direction*(390 if self.sliding and self.stone_boost
                             else 365 if self.sliding else move_speed)*dt
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
            game.audio.play('fall')
            if not game.consume_life(False):
                return
            self.reset_position()
            self.say('목숨이 하나 줄었어요 · 입구에서 다시 출발! 봉인석은 유지됩니다.')
            return
        for i,stone in enumerate(self.stones):
            if i not in self.state['stones'] and self.player.colliderect(stone):
                self.state['stones'].add(i)
                self.pulses.append((stone.center,0.8))
                game.audio.play('collect')
                self.stone_boost = 5.0
                self.invincible = max(self.invincible, 0.8)
                self.say(f"봉인석 {len(self.state['stones'])}/3 · 결정의 힘으로 이동 가속 5초!")
        for i,enemy in list(self.enemies):
            enemy.update(dt,self.player)
            damage_box = enemy.damage_hitbox()
            stomp_box = enemy.stomp_hitbox()
            can_stomp = (self.vy > 0
                         and previous_bottom <= stomp_box.top+5
                         and self.player.bottom >= stomp_box.top
                         and self.player.right > stomp_box.left
                         and self.player.left < stomp_box.right)
            if self.player.colliderect(damage_box) or can_stomp:
                if can_stomp:
                    self.enemies.remove((i,enemy))
                    self.state['defeated'].add(i)
                    game.score += enemy.points
                    game.audio.play('defeat')
                    self.vy = -400
                    self.player.bottom = stomp_box.top
                    self.y = float(self.player.y)
                    self.grounded = False
                    self.invincible = max(self.invincible, 0.45)
                    self.pulses.append((enemy.rect.center,0.8))
                    break
                elif not self.invincible:
                    game.audio.play('hit')
                    if not game.consume_life(True):
                        return
                    self.hurt = 0.35
                    self.say('피격! 목숨이 하나 줄어 입구로 돌아갑니다.')
                    return
        target = max(0,min(self.WIDTH-800,self.player.centerx-400))
        self.camera += (target-self.camera)*(1-math.exp(-10*dt))
        game.animation.update(dt,self.player,self.vy,self.grounded,was_grounded,abs(self.player.x-previous_x))

    def draw(self, game, screen):
        # One continuous panorama covers the full scroll range without seams.
        atmosphere = self.atmosphere_layer
        atmosphere.fill((0, 0, 0, 0))
        atmosphere.fill((8,27,50,55) if self.index==0 else (30,19,50,75))
        background_drift = round(400 * max(0, min(1, self.camera /
                                                   (self.WIDTH-800))))
        screen.blit(self.background, (-background_drift, 0))
        screen.blit(atmosphere,(0,0))
        # Mineral seams, strata and distant rock silhouettes are baked into the
        # panorama, avoiding duplicate geometric overlays and per-frame work.
        dust_count = {'performance':12, 'balanced':22, 'high':35}[game.quality]
        for i in range(dust_count):
            x = round((i*137+self.time*6)%self.WIDTH-self.camera*0.65)
            y = 240+(i*67)%300
            pg.draw.circle(screen,(80,132,154),(x,y),1)
        # Low mist softens the hard join between the scrolling wall and floor.
        mist = self.mist_layer
        mist.fill((0, 0, 0, 0))
        mist_bands = {'performance':3, 'balanced':4, 'high':5}[game.quality]
        for band in range(mist_bands):
            alpha = 22-band*3
            y = 18+band*14+round(math.sin(self.time*.5+band)*3)
            pg.draw.ellipse(mist, (133,202,215,alpha), (-90+band*105,y,420,48))
            pg.draw.ellipse(mist, (133,202,215,alpha), (330+band*80,y+5,430,42))
        screen.blit(mist, (0,508))
        # The entrance belongs to the rear wall. Platforms and their top edge
        # cover its base, so it reads as an opening cut into the ice.
        entrance_x = round(80-self.camera)
        game.art.grounded(screen,self.entrance_image,(entrance_x,550),snow=False)
        # Darken the doorway itself so the ice frame belongs to the rear wall;
        # the player is drawn later and remains readable inside the opening.
        pg.draw.ellipse(screen,(7,24,38),(entrance_x-31,474,62,76))
        pg.draw.arc(screen,(82,148,170),(entrance_x-35,470,70,83),
                    math.pi,math.tau,2)
        for platform in self.active_platforms():
            rect = platform.move(-self.camera,0)
            if rect.right < -60 or rect.left > 860:
                continue
            kind = ('crumble' if tuple(platform) in self.fragile else
                    'cave' if self.index == 0 else 'fracture')
            if tuple(platform) in self.crumbles:
                elapsed = self.crumbles[tuple(platform)][0]
                rect.move_ip(round(math.sin(elapsed*60)*elapsed*5),round(math.sin(elapsed*45)*elapsed*2))
            ground = platform in self.grounds
            variant = ('ground' if ground else
                       'thin' if platform.width <= 120 else 'normal')
            screen.blit(game.platform_texture(kind, platform.size, ground,
                                               (False, False), variant), rect)
        if self.arch:
            arch = self.arch.move(-self.camera,0)
            # Use the same painted material as the cave platforms so the low
            # slide tunnel reads as a natural ice shelf, not a UI rectangle.
            arch_kind = 'cave' if self.index == 0 else 'fracture'
            if self.arch_image is None:
                arch_image = game.platform_texture(arch_kind, arch.size)
                self.arch_image = pg.transform.flip(arch_image, False, True)
            screen.blit(self.arch_image, arch)
            pg.draw.line(screen, (176, 231, 239),
                         (arch.left+8, arch.bottom-2),
                         (arch.right-8, arch.bottom-2), 2)
        for i,stone in enumerate(self.stones):
            if i in self.state['stones']:
                continue
            rect = stone.move(-self.camera,round(math.sin(self.time*2+i)*3))
            image = game.art.gameplay[
                'seal-stone-blue' if self.index == 0 else 'seal-stone-violet']
            screen.blit(image, image.get_rect(center=rect.center))
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
        ui.panel(screen,(12,12,776,62))
        ui.text(screen,self.TITLES[self.index],(28,23),ui.heading)
        ui.text(screen,'선택 탐험 · 입구에서 E로 언제든 귀환',(28,56),ui.small)
        ui.text(screen,f"봉인석 {len(self.state['stones'])}/3",(470,26),ui.heading)
        ui.text(screen,'보물 발견' if game.caves[self.index]['treasure'] else '보물방 열림' if self.state['lever'] else '보물방 봉인',(650,28),ui.body)
        ui.text(screen,f'{game.score}점',(595,57),ui.small)
        ui.text(screen,'목숨',(670,57),ui.small)
        ui.life_icons(screen,game,(718,59),(15,19),21)
        message = self.notice if self.notice_left else ('E: 해안으로 귀환' if self.player.centerx<170 else
                  'E: 봉인 레버 작동' if self.near(self.lever) else
                  'E: 보물 상자 열기' if self.state['lever'] and self.near(self.chest) else
                  'E: 위쪽 지름길로 나가기' if self.near(self.exit) else '')
        if message:
            ui.panel(screen,(150,82,500,34),dark=True)
            ui.text(screen,message,(400,99),ui.small,'white',center=True,max_width=470)
