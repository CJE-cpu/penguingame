"""Rescue quests, optional ocean exploration, journals and a growing home."""
import math
import pygame as pg

JOURNALS = [
    ('해안의 첫 발자국', '배를 눈에 붙이면 바람처럼 미끄러질 수 있다.'),
    ('얼음에 갇힌 친구', '빙하의 친구는 얼음 껍질을 깨야 함께 갈 수 있다.'),
    ('동굴의 비밀', '동굴 입구의 푸른 빛은 위쪽 통로로 이어진다.'),
    ('눈보라 속 식사', '배고픈 친구에게 물고기 세 마리를 나눠 주었다.'),
    ('빙붕 탈출 기록', '무너지는 빙붕을 건너면 보금자리가 보인다.'),
    ('함께 만든 집', '돌아온 친구들과 작은 둥지를 꾸미기로 했다.')]
HOME_UPGRADES = [('따뜻한 둥지', 5), ('탐험 깃발', 8), ('얼음 꽃밭', 10)]
OXYGEN_DURATION = 35.0


class AdventureContent:
    def __init__(self, game):
        self.reset(game)

    def reset(self, game):
        self.wallet = 0
        self.upgrades = 0
        self.book_open = False
        self.sliding = False
        self.quests = [False, False, False]
        self.journals = []
        for region, ledges in enumerate(game.region_ledges):
            platform = ledges[1]
            self.journals.append({'rect': pg.Rect(platform.left+24, platform.top-32, 23, 29), 'found': False})
        platform = min(game.region_ledges[5], key=lambda p:p.y)
        self.lever = pg.Rect(platform.left+20, platform.top-34, 25, 34)
        self.hole = pg.Rect(670, 533, 64, 17)
        self.diving = False
        self.oxygen = OXYGEN_DURATION
        self.swimmer = pg.Vector2(100, 115)
        self.dive_return = None
        self.ocean_fish = [(kind, pg.Rect(x,y,36,24)) for kind,x,y in
                           [('orange',300,230),('blue',550,390),('orange',800,220),
                            ('gold',1040,450),('blue',1300,280),('gold',1540,400)]]
        self.escape_active = False
        self.escape_cleared = False
        self.escape_left = 24.0
        self.notice = ''
        self.notice_left = 0.0

    def say(self, text):
        self.notice, self.notice_left = text, 3.0

    def nearby(self, game, rect, distance=85):
        return abs(game.player.centerx-rect.centerx)<distance and abs(game.player.bottom-rect.bottom)<70

    def action(self, game):
        if self.book_open:
            self.book_open = False
            return
        if self.diving:
            if self.swimmer.distance_to((100,115)) < 85:
                self.leave_ocean(game)
            else:
                self.say('왼쪽 위 얼음 구멍으로 돌아가세요!')
            return
        if game.combat.hurt:
            return
        baby = game.babies[1]
        if not baby['rescued'] and not self.quests[1] and self.nearby(game,baby['rect']):
            if self.wallet >= 3:
                self.wallet -= 3
                self.quests[1] = True
                self.say('물고기를 나눠 주었어요! 친구와 함께 이글루로!')
            else:
                self.say('배고픈 친구에게 줄 물고기 3마리가 필요해요.')
            return
        if not self.quests[2] and self.nearby(game,self.lever,55):
            self.quests[2] = True
            self.say('길 안내 깃발을 세웠어요! 마지막 친구에게 가세요.')
            return
        if self.nearby(game,self.hole,65):
            if game.carried_baby is not None:
                self.say('친구를 먼저 이글루에 데려다 주세요.')
            else:
                self.diving = True
                self.oxygen = OXYGEN_DURATION
                self.swimmer.update(100,115)
                self.dive_return = game.player.midbottom
                self.say('잠수! 방향키로 수영 · 왼쪽 위 구멍에서 E로 나가기')
                game.coach.explain('swim')
            return
        home = game.checkpoints[-1]
        if self.nearby(game,home):
            if not game.fish and game.rescued == 3 and not self.escape_cleared:
                game.player.midbottom = (4855,550)
                game.x, game.y = map(float,game.player.topleft)
                game.velocity_x = game.velocity_y = 0
                game.camera_x = 4480
                self.begin_escape()
            elif self.upgrades < len(HOME_UPGRADES):
                name, cost = HOME_UPGRADES[self.upgrades]
                if self.wallet >= cost:
                    self.wallet -= cost
                    self.upgrades += 1
                    self.say(name+' 완성! 친구들이 좋아해요.')
                else:
                    self.say(f'{name}: 물고기 {cost}마리가 필요해요.')
            else:
                self.say('우리 보금자리 꾸미기 완료! TAB으로 탐험 일지를 보세요.')
            return
        for index,cave in enumerate(game.caves):
            if self.nearby(game,cave['rect'],105):
                ledges = game.region_ledges[2 if index==0 else 4]
                platform = min(ledges,key=lambda p:p.y)
                game.player.midbottom = (platform.left+28,platform.top)
                game.x, game.y = map(float,game.player.topleft)
                game.velocity_x = game.velocity_y = 0
                game.on_ground = True
                game.invincible = max(game.invincible,1)
                game.companion.reset()
                self.say('숨겨진 동굴 통로를 발견했어요!')
                return

    def leave_ocean(self, game):
        self.diving = False
        game.player.midbottom = self.dive_return
        game.x, game.y = map(float,game.player.topleft)
        game.velocity_x = game.velocity_y = 0
        game.on_ground = True
        self.say('잠수 탐험 완료! 모은 물고기로 집을 꾸며 보세요.')

    def begin_escape(self):
        self.escape_active = True
        self.escape_left = 24.0
        self.say('빙붕 탈출! 24초 안에 오른쪽 보금자리로!')

    def update(self, game, dt):
        self.notice_left = max(0,self.notice_left-dt)
        for journal in self.journals:
            if not journal['found'] and game.player.colliderect(journal['rect']):
                journal['found'] = True
                game.score += 60
                game.feedback.emit(journal['rect'].center,'탐험 일지! +60',(255,224,124))
                self.say('탐험 일지 발견! TAB으로 읽어 보세요.')
        baby = game.babies[0] if game.babies else None
        if baby and not self.quests[0] and self.sliding and abs(game.velocity_x)>40 and self.nearby(game,baby['rect'],80):
            self.quests[0] = True
            game.feedback.emit(baby['rect'].center,'얼음 껍질 돌파!',(132,224,255))
            self.say('얼음에 갇힌 친구를 구했어요! 이글루로 데려가세요.')
        if not self.escape_cleared and not self.escape_active and 4800 <= game.player.centerx <= 4930:
            self.begin_escape()
        if self.escape_active:
            self.escape_left -= dt
            if game.player.centerx >= 5960:
                self.escape_active = False
                self.escape_cleared = True
                game.score += 200
                self.say('빙붕 탈출 성공! +200점 · 보금자리로 돌아가세요.')
            elif self.escape_left <= 0:
                game.respawn()
                self.say('빙붕 탈출 시간 초과! 입구에서 다시 도전하세요.')

    def swim(self, game, dt, direction, vertical):
        game.animation.clock += dt
        self.notice_left = max(0,self.notice_left-dt)
        self.oxygen -= dt
        movement = pg.Vector2(direction,vertical)
        if movement.length_squared()>1:
            movement.normalize_ip()
        self.swimmer += movement*235*dt
        self.swimmer.x = max(35,min(1765,self.swimmer.x))
        self.swimmer.y = max(100,min(525,self.swimmer.y))
        if direction:
            game.facing_right = direction>0
        rect = pg.Rect(0,0,52,35)
        rect.center = self.swimmer
        remaining = []
        for kind,fish in self.ocean_fish:
            if rect.colliderect(fish):
                points = {'orange':10,'blue':25,'gold':50}[kind]
                game.score += points
                self.wallet += 1
                self.say(f'바닷속 물고기 발견! +{points}점')
            else:
                remaining.append((kind,fish))
        self.ocean_fish = remaining
        if self.oxygen <= 0:
            self.diving = False
            game.respawn()
            self.say('산소가 떨어졌어요! 모은 물고기는 유지됩니다.')

    def context(self, game):
        for index,baby in enumerate(game.babies):
            if not baby['rescued'] and not self.quests[index] and self.nearby(game,baby['rect'],120):
                return ['↓ + 이동: 얼음 껍질 깨기','E: 물고기 3마리 나눠 주기','위쪽 옆길의 깃발 레버를 찾아 E'][index]
        if not self.quests[2] and self.nearby(game,self.lever):
            return 'E: 길 안내 깃발 세우기'
        if self.nearby(game,self.hole):
            return 'E: 바닷속 탐험 · 산소 35초 · 구멍으로 돌아오기'
        if self.nearby(game,game.checkpoints[-1]):
            if not game.fish and game.rescued==3 and not self.escape_cleared:
                return 'E: 마지막 빙붕 탈출 도전'
            if self.upgrades<len(HOME_UPGRADES):
                name,cost = HOME_UPGRADES[self.upgrades]
                return f'E: {name} 만들기 · 물고기 {cost}마리'
            return '우리 보금자리 완성! TAB: 탐험 일지'
        if any(self.nearby(game,c['rect'],105) for c in game.caves):
            return 'E: 동굴의 숨겨진 위쪽 통로'
        return ''

    def draw_world(self, game, screen):
        for journal in self.journals:
            if journal['found']:
                continue
            rect = journal['rect'].move(-game.camera_x,round(math.sin(game.time*3)*3))
            pg.draw.rect(screen,(239,197,104),rect,border_radius=3)
            pg.draw.rect(screen,(91,65,55),rect,2,border_radius=3)
            pg.draw.line(screen,(255,250,221),(rect.x+6,rect.y+8),(rect.right-4,rect.y+8),2)
            pg.draw.line(screen,(255,250,221),(rect.x+6,rect.y+15),(rect.right-4,rect.y+15),2)
        hole = self.hole.move(-game.camera_x,0)
        pg.draw.ellipse(screen,(6,52,97),hole)
        pg.draw.ellipse(screen,(157,235,252),hole,3)
        if -100<hole.x<900:
            game.ui.text(screen,'잠수 E',(hole.x-3,hole.y-23),game.ui.small)
        for index,baby in enumerate(game.babies):
            if self.quests[index] or baby['rescued']:
                continue
            rect = baby['rect'].move(-game.camera_x,0)
            if index==0:
                pg.draw.rect(screen,(111,205,245),rect.inflate(14,12),3,border_radius=10)
                pg.draw.line(screen,(206,248,255),rect.topleft,rect.bottomright,2)
            else:
                game.ui.icon(screen,game.fish_images['orange'] if index==1 else game.igloo_image,
                             (rect.centerx,rect.top-43),(25,21))
        lever = self.lever.move(-game.camera_x,0)
        pg.draw.line(screen,(93,89,105),lever.midbottom,(lever.centerx,lever.top),4)
        pg.draw.polygon(screen,(141,232,168) if self.quests[2] else (255,204,99),
                        [(lever.centerx,lever.top),(lever.right+8,lever.top+5),(lever.centerx,lever.top+15)])
        home = game.checkpoints[-1]
        cx, floor = round(home.centerx-game.camera_x),home.bottom
        if self.upgrades>=1:
            pg.draw.ellipse(screen,(151,111,71),(cx+72,floor-13,65,13))
            pg.draw.ellipse(screen,(245,220,151),(cx+78,floor-11,53,8),2)
        if self.upgrades>=2:
            pg.draw.line(screen,(69,108,133),(cx+155,floor),(cx+155,floor-70),4)
            pg.draw.polygon(screen,(246,188,88),[(cx+155,floor-70),(cx+195,floor-59),(cx+155,floor-46)])
        if self.upgrades>=3:
            for i in range(5):
                x = cx+213+i*17
                pg.draw.line(screen,(83,170,154),(x,floor),(x,floor-17),2)
                pg.draw.circle(screen,(149,228,250),(x,floor-20),6)
                pg.draw.circle(screen,(255,235,135),(x,floor-20),2)
        for i,baby in enumerate(game.babies):
            if not baby['rescued']:
                continue
            x = cx+70+i*47+round(math.sin(game.time*0.8+i)*18)
            image = pg.transform.rotate(game.baby_image,math.sin(game.time*5+i)*5)
            screen.blit(image,image.get_rect(midbottom=(x,floor)))

    def draw_hud(self, game, screen):
        game.ui.panel(screen,(283,147,208,43))
        game.ui.text(screen,f'먹이 {self.wallet} · 일지 {sum(j["found"] for j in self.journals)}/6',(297,150),game.ui.small)
        game.ui.text(screen,'↓ 활주 · E 행동 · TAB 일지',(297,169),game.ui.small)
        message = self.notice if self.notice_left else self.context(game)
        if self.escape_active:
            message = f'빙붕 탈출 {max(0,self.escape_left):.1f}초 · 오른쪽 끝까지!'
        if message:
            game.ui.panel(screen,(100,510,600,39),dark=True)
            game.ui.text(screen,message,(400,529),game.ui.small,'white',center=True)

    def draw_book(self, game, screen):
        game.ui.veil(screen)
        game.ui.panel(screen,(78,65,644,475))
        game.ui.text(screen,'펭귄 탐험 일지',(400,99),game.ui.heading,center=True)
        for i,(title,text) in enumerate(JOURNALS):
            y = 137+i*56
            found = self.journals[i]['found']
            game.ui.text(screen,f'{i+1}. '+(title if found else '아직 찾지 못한 기록'),(106,y),game.ui.body)
            game.ui.text(screen,text if found else '해당 구역의 위쪽 옆길을 살펴보세요.',(106,y+25),game.ui.small)
        game.ui.text(screen,'TAB / E: 닫기 · 일지를 읽는 동안 모험이 멈춥니다.',(400,504),game.ui.small,center=True)

    def draw_ocean(self, game, screen):
        screen.fill((15,68,113))
        camera = max(0,min(1000,self.swimmer.x-400))
        for y in range(90,550,15):
            pg.draw.rect(screen,(13,max(29,81-y//12),max(63,140-y//9)),(0,y,800,15))
        pg.draw.rect(screen,(208,239,248),(0,65,800,25))
        pg.draw.ellipse(screen,(67,142,181),(60-camera,77,80,19))
        pg.draw.rect(screen,(13,42,67),(0,550,800,50))
        for i in range(20):
            x = round(i*97-camera)
            height = 25+int(math.sin(i)*15)
            pg.draw.line(screen,(74,166,151),(x,550),(x+round(math.sin(game.time*2+i)*8),550-height),4)
        for i in range(24):
            x = round((i*83+math.sin(game.time+i)*9)%1800-camera)
            y = round(540-(game.time*28+i*37)%425)
            pg.draw.circle(screen,(104,181,211),(x,y),3,1)
        for kind,rect in self.ocean_fish:
            screen.blit(game.fish_images[kind],rect.move(-camera,round(math.sin(game.time*4+rect.x)*4)))
        image = game.animation.action_image('swim',game.facing_right)
        screen.blit(image,image.get_rect(center=(round(self.swimmer.x-camera),round(self.swimmer.y))))
        for i in range(5):
            phase = (game.animation.clock*1.4+i/5)%1
            side = -1 if game.facing_right else 1
            x = round(self.swimmer.x-camera+side*(35+phase*40))
            y = round(self.swimmer.y-5-phase*12)
            pg.draw.circle(screen,(136,210,234),(x,y),max(1,round(3*(1-phase))),1)
        game.ui.panel(screen,(12,12,776,56))
        game.ui.text(screen,f'남극 바닷속 탐험 · 산소 {max(0,self.oxygen):.1f}초',(29,24),game.ui.body)
        game.ui.text(screen,f'먹이 {self.wallet} · 보너스 물고기 {6-len(self.ocean_fish)}/6',(520,26),game.ui.small)
        pg.draw.rect(screen,(107,218,239),(30,54,round(450*max(0,self.oxygen)/OXYGEN_DURATION),5))
        game.ui.panel(screen,(12,563,776,30))
        game.ui.text(screen,'방향키 / WASD 수영 · 왼쪽 위 구멍에서 E로 나가기 · 산소가 떨어지기 전에 귀환!',(28,569),game.ui.small)
        game.ui.text(screen,'출구 E' if camera<140 else '← 출구로 귀환',
                     (max(18,round(75-camera)),75 if camera<140 else 100),game.ui.small,'white')
        if self.notice_left:
            game.ui.text(screen,self.notice,(400,535),game.ui.small,'white',center=True)
