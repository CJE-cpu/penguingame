"""Rescue quests, optional ocean exploration, journals and a growing home."""
import math
import pygame as pg

JOURNALS = [
    ('해안의 첫 발자국', '첫 이글루 오른쪽의 넓은 눈밭 끝에서 잠수 구멍을 찾았다. E로 들어가면 왼쪽 위에 출구가 있다.\n산소 35초 안에 귀환해야 한다. 깊은 곳의 황금 물고기를 찾더라도 산소가 절반 남으면 귀환을 준비하자.\n↓를 누르며 이동하면 1.35배로 활주한다. 서두르지 말고 순찰하는 적과 거리를 두자.'),
    ('얼음에 갇힌 친구', '빙하의 가장 높은 발판 오른쪽에 아기 펭귄이 얼음 껍질에 갇혀 있다. 발판 위에 착지한 뒤 ↓를 누르며 가까이 이동하면 껍질이 깨진다.\n친구가 따라오기 시작하면 가까운 이글루로 데려가자. 몸에 닿는 것만으로 구조가 완료되지는 않는다.\n거대 물약은 8초간 적을 돌파한다. 종료 직후에는 1.5초의 보호 시간이 있어 안전한 곳으로 이동할 수 있다.'),
    ('동굴의 비밀', '동굴 구역과 빙붕 구역 오른쪽 땅의 얼음 입구에서 E를 누르면 별도의 내부를 탐험한다. 푸른 동굴은 낮은 활주 통로, 빙붕 동굴은 무너지는 다리가 특징이다.\n봉인석 3개를 찾아 오른쪽 레버에서 E로 보물방을 연다. 상자에서 E로 100점을 얻고, 끝의 출구에서 E로 나오면 150점과 먹이 3개, 높은 옆길로 이어지는 지름길을 얻는다.\n입구 근처 E로 언제든 돌아올 수 있다. 찾은 봉인석과 보물 기록은 유지되고, 같은 보상은 두 번 지급되지 않는다. 반전 물약은 바깥 동굴 구역의 오른쪽 위 옆길에 한 개 있다.'),
    ('눈보라 속 식사', '눈보라 구역의 가장 높은 발판 오른쪽에서 배고픈 친구를 만났다. 먹이 3마리를 가진 채 가까이서 E를 누르면 친구가 따라온다.\n먹이는 물고기 한 마리를 주울 때 한 개씩 늘어난다. 나눠 줘도 점수와 30마리 수집 목표는 줄어들지 않는다.\n바람은 왼쪽으로 분다. 속도 물약과 활주를 이용하되, 갈매기가 낮게 내려올 때는 잠시 기다리자.'),
    ('빙붕 탈출 기록', '갈라진 빙붕 입구부터 오른쪽 끝까지 32초 안에 건너면 탈출 성공이다. 발판은 밟은 뒤 0.8초에 무너지고 4초 뒤 복구된다.\n위쪽 길의 결정은 선택 수집품이다. 탈출 도중 억지로 돌아가지 말고, 완료 기록을 남긴 후 천천히 다시 찾아도 된다.\n추락하거나 시간이 끝나도 물고기, 일지와 구조 기록은 유지된다. 입구에서 도전을 다시 시작할 수 있다.'),
    ('함께 만든 집', '보금자리의 가장 높은 발판 왼쪽에 길 안내 레버가 있다. 가까이서 E를 눌러 초록 깃발을 세운 뒤 오른쪽 친구를 만나자.\n마지막 이글루에서는 먹이 5개로 둥지, 8개로 깃발, 10개로 꽃밭을 만든다. 연구 의뢰 보상도 먹이로 사용할 수 있다.\n마지막 이글루에 도착하면 모험이 끝난다. 물고기, 친구와 두 동굴의 보물을 얼마나 모았는지에 따라 네 가지 엔딩 중 하나가 열린다.')]
HOME_UPGRADES = [('따뜻한 둥지', 5), ('탐험 깃발', 8), ('얼음 꽃밭', 10)]
OXYGEN_DURATION = 35.0
ESCAPE_DURATION = 32.0
RESEARCH_TASKS = [('해양 생태 조사',3,100,2),('탐험 기록 복원',3,150,3),('빙하 결정 조사',6,250,5)]


class AdventureContent:
    def __init__(self, game):
        self.reset(game)

    def reset(self, game):
        self.wallet = 0
        self.upgrades = 0
        self.book_open = False
        self.book_page = 0
        self.sliding = False
        self.quests = [False, False, False]
        self.journals = []
        for region, ledges in enumerate(game.region_ledges):
            platform = ledges[1]
            self.journals.append({'rect': pg.Rect(platform.left+24, platform.top-32, 23, 29), 'found': False})
        platform = min(game.region_ledges[5], key=lambda p:p.y)
        self.lever = pg.Rect(platform.left+20, platform.top-34, 25, 34)
        ground = game.region_grounds[0][0]
        self.hole = pg.Rect(ground.right-95,ground.top-17,64,17)
        self.crystals = []
        for ledges in game.region_ledges:
            platform = ledges[-2]
            self.crystals.append({'rect':pg.Rect(platform.left+40,platform.top-30,20,26),'found':False})
        self.research_claimed = [False,False,False]
        self.escape_start = 4*game.region_width
        self.escape_end = 5*game.region_width-40
        self.diving = False
        self.oxygen = OXYGEN_DURATION
        self.swimmer = pg.Vector2(100, 115)
        self.dive_return = None
        self.ocean_rings = []
        self.ocean_fish = [(kind, pg.Rect(x,y,36,24)) for kind,x,y in
                           [('orange',300,230),('blue',550,390),('orange',800,220),
                            ('gold',1040,450),('blue',1300,280),('gold',1540,400)]]
        self.escape_active = False
        self.escape_cleared = False
        self.escape_left = ESCAPE_DURATION
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
                game.animation.swim_angle = 0.0
                game.animation.swim_movement.update(0,0)
                self.dive_return = game.player.midbottom
                self.say('잠수! 방향키로 수영 · 왼쪽 위 구멍에서 E로 나가기')
                game.coach.explain('swim')
            return
        if any(self.nearby(game,checkpoint) for checkpoint in game.checkpoints):
            progress = self.research_progress()
            for i,(name,goal,points,food) in enumerate(RESEARCH_TASKS):
                if not self.research_claimed[i] and progress[i]>=goal:
                    self.research_claimed[i] = True
                    game.score += points
                    self.wallet += food
                    self.say(f'{name} 완료! +{points}점 · 먹이 +{food}')
                    return
        home = game.checkpoints[-1]
        if self.nearby(game,home):
            if not game.fish and game.rescued == 3 and not self.escape_cleared:
                game.player.midbottom = (self.escape_start+55,550)
                game.x, game.y = map(float,game.player.topleft)
                game.velocity_x = game.velocity_y = 0
                game.camera_x = self.escape_start-320
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
                if game.carried_baby is not None:
                    self.say('친구를 먼저 이글루에 데려다 주세요.')
                    return
                from cave import CaveExpedition
                game.cave_expedition = CaveExpedition(game,index)
                cave['found'] = True
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
        self.escape_left = ESCAPE_DURATION
        self.say('빙붕 탈출! 32초 안에 오른쪽 보금자리로!')

    def research_progress(self):
        return [6-len(self.ocean_fish),sum(j['found'] for j in self.journals),sum(c['found'] for c in self.crystals)]

    def update(self, game, dt):
        self.notice_left = max(0,self.notice_left-dt)
        for index,journal in enumerate(self.journals):
            if not journal['found'] and game.player.colliderect(journal['rect']):
                journal['found'] = True
                self.book_page = index
                game.score += 60
                game.feedback.emit(journal['rect'].center,'탐험 일지! +60',(255,224,124))
                self.say('탐험 일지 발견! TAB으로 읽어 보세요.')
        for crystal in self.crystals:
            if not crystal['found'] and game.player.colliderect(crystal['rect']):
                crystal['found'] = True
                game.score += 40
                game.feedback.emit(crystal['rect'].center,'빙하 결정! +40',(128,227,255))
                self.say('빙하 결정 발견! 6개를 모아 이글루에서 E로 조사 보상 받기')
        baby = game.babies[0] if game.babies else None
        if baby and not self.quests[0] and self.sliding and abs(game.velocity_x)>40 and self.nearby(game,baby['rect'],80):
            self.quests[0] = True
            game.feedback.emit(baby['rect'].center,'얼음 껍질 돌파!',(132,224,255))
            self.say('얼음에 갇힌 친구를 구했어요! 이글루로 데려가세요.')
        if not self.escape_cleared and not self.escape_active and self.escape_start <= game.player.centerx <= self.escape_start+130:
            self.begin_escape()
        if self.escape_active:
            self.escape_left -= dt
            if game.player.centerx >= self.escape_end:
                self.escape_active = False
                self.escape_cleared = True
                game.score += 200
                self.say('빙붕 탈출 성공! +200점 · 보금자리로 돌아가세요.')
            elif self.escape_left <= 0:
                game.respawn()
                self.say('빙붕 탈출 시간 초과! 입구에서 다시 도전하세요.')

    def swim(self, game, dt, direction, vertical):
        self.notice_left = max(0,self.notice_left-dt)
        self.oxygen -= dt
        movement = pg.Vector2(direction,vertical)
        if movement.length_squared()>1:
            movement.normalize_ip()
        self.swimmer += movement*235*dt
        self.swimmer.x = max(35,min(1765,self.swimmer.x))
        self.swimmer.y = max(125,min(500,self.swimmer.y))
        if direction:
            game.facing_right = direction>0
        game.animation.update_swim(dt,movement,game.facing_right)
        self.ocean_rings = [(pos,life-dt) for pos,life in self.ocean_rings if life>dt]
        rect = pg.Rect(0,0,52,35)
        rect.center = self.swimmer
        remaining = []
        for kind,fish in self.ocean_fish:
            if rect.colliderect(fish):
                points = {'orange':10,'blue':25,'gold':50}[kind]
                game.score += points
                self.wallet += 1
                self.ocean_rings.append((fish.center,0.65))
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
        if any(self.nearby(game,checkpoint) for checkpoint in game.checkpoints):
            progress = self.research_progress()
            for i,(name,goal,points,food) in enumerate(RESEARCH_TASKS):
                if not self.research_claimed[i] and progress[i]>=goal:
                    return f'E: {name} 보상 · +{points}점 / 먹이 +{food}'
        if self.nearby(game,game.checkpoints[-1]):
            if not game.fish and game.rescued==3 and not self.escape_cleared:
                return 'E: 마지막 빙붕 탈출 도전'
            if self.upgrades<len(HOME_UPGRADES):
                name,cost = HOME_UPGRADES[self.upgrades]
                return f'E: {name} 만들기 · 물고기 {cost}마리'
            return '우리 보금자리 완성! TAB: 탐험 일지'
        if any(self.nearby(game,c['rect'],105) for c in game.caves):
            return 'E: 동굴 탐험 · 봉인석 3개와 보물 찾기'
        return ''

    def draw_world(self, game, screen):
        for index,crystal in enumerate(self.crystals):
            if crystal['found']:
                continue
            rect = crystal['rect'].move(-game.camera_x,round(math.sin(game.time*3+index)*3))
            cx,cy = rect.center
            pg.draw.polygon(screen,(43,133,195),[(cx,rect.top),(rect.right,cy),(cx,rect.bottom),(rect.left,cy)])
            pg.draw.polygon(screen,(148,238,255),[(cx,rect.top+2),(cx+7,cy),(cx,rect.bottom-3),(cx-7,cy)])
            pg.draw.line(screen,(239,255,255),(cx,rect.top+4),(cx-5,cy),2)
        for journal in self.journals:
            if journal['found']:
                continue
            rect = journal['rect'].move(-game.camera_x,round(math.sin(game.time*3)*3))
            game.art.place(screen,'journal',rect.midbottom)
        hole = self.hole.move(-game.camera_x,0)
        game.art.place(screen,'dive-hole',hole.midbottom)
        for index,baby in enumerate(game.babies):
            if self.quests[index] or baby['rescued']:
                continue
            rect = baby['rect'].move(-game.camera_x,0)
            if index==0:
                game.art.place(screen,'ice-cage',(rect.centerx,rect.bottom+4))
            else:
                game.ui.icon(screen,game.fish_images['orange'] if index==1 else game.igloo_image,
                             (rect.centerx,rect.top-43),(25,21))
        lever = self.lever.move(-game.camera_x,0)
        game.art.place(screen,'lever-up' if self.quests[2] else 'lever-down',lever.midbottom)
        home = game.checkpoints[-1]
        cx, floor = round(home.centerx-game.camera_x),home.bottom
        if self.upgrades>=1:
            game.art.place(screen,'nest',(cx+104,floor))
        if self.upgrades>=2:
            game.art.place(screen,'home-flag',(cx+172,floor))
        if self.upgrades>=3:
            game.art.place(screen,'flowers',(cx+252,floor))
        for i,baby in enumerate(game.babies):
            if not baby['rescued']:
                continue
            phase = game.time*0.8+i
            x = cx+70+i*47+round(math.sin(phase)*18)
            image = game.art.baby('walk',game.time+i*0.3,math.cos(phase)>0)
            screen.blit(image,image.get_rect(midbottom=(x,floor)))

    def draw_hud(self, game, screen):
        game.ui.panel(screen,(283,147,208,43))
        game.ui.text(screen,f'먹이 {self.wallet} · 일지 {sum(j["found"] for j in self.journals)}/6',(297,150),game.ui.small)
        game.ui.text(screen,f'결정 {sum(c["found"] for c in self.crystals)}/6 · TAB 기록/의뢰',(297,169),game.ui.small)
        message = self.notice if self.notice_left else self.context(game)
        if self.escape_active:
            message = f'빙붕 탈출 {max(0,self.escape_left):.1f}초 · 오른쪽 끝까지!'
        if message:
            game.ui.panel(screen,(100,202,600,35),dark=True)
            game.ui.text(screen,message,(400,219),game.ui.small,'white',center=True,max_width=570)

    def draw_book(self, game, screen):
        game.ui.veil(screen)
        game.ui.panel(screen,(78,65,644,475))
        game.ui.text(screen,'펭귄 탐험 일지',(400,99),game.ui.heading,center=True)
        game.ui.icon(screen,game.art.objects['journal-open'],(120,101),(38,28))
        if self.book_page==6:
            game.ui.text(screen,'남극 연구 기지의 의뢰',(106,141),game.ui.heading)
            progress = self.research_progress()
            tips = ['해안 얼음 구멍으로 잠수해 보너스 물고기를 찾으세요.',
                    '각 구역 두 번째 위쪽 발판 왼쪽에서 일지를 찾으세요.',
                    '구역마다 높은 옆길의 푸른 결정을 한 개씩 모으세요.']
            for i,(name,goal,points,food) in enumerate(RESEARCH_TASKS):
                y = 188+i*89
                status = '보상 수령' if self.research_claimed[i] else 'E로 수령 가능' if progress[i]>=goal else '조사 중'
                game.ui.text(screen,f'{name} · {min(goal,progress[i])}/{goal} · {status}',(106,y),game.ui.body)
                game.ui.text(screen,tips[i],(106,y+28),game.ui.small)
                game.ui.text(screen,f'보상: {points}점 / 먹이 {food}개 · 아무 이글루 근처에서 E',(106,y+50),game.ui.small)
        else:
            title,text = JOURNALS[self.book_page]
            found = self.journals[self.book_page]['found']
            game.ui.text(screen,f'{self.book_page+1}. '+title,(106,141),game.ui.heading)
            if not found:
                text = f'{self.book_page+1}번째 구역의 두 번째 위쪽 발판 왼쪽에서 이 기록을 찾으세요.\n기록에는 해당 구역 친구의 부탁, 위험 요소, 숨겨진 길과 조작 방법이 담겨 있습니다.\n일지 3개를 찾으면 연구 의뢰 보상을 받을 수 있습니다. →로 연구 의뢰 페이지도 확인해 보세요.'
            lines = []
            for paragraph in text.split('\n'):
                current = ''
                for char in paragraph:
                    if game.ui.body.size(current+char)[0]>585:
                        lines.append(current)
                        current = char
                    else:
                        current += char
                lines.append(current)
                lines.append('')
            for index,line in enumerate(lines):
                game.ui.text(screen,line,(106,185+index*24),game.ui.body)
        game.ui.text(screen,f'← → 페이지 {self.book_page+1}/7 · TAB / E 닫기 · 모험 일시정지',(400,504),game.ui.small,center=True)

    def draw_water_light(self, screen, time, camera):
        light = pg.Surface(screen.get_size(),pg.SRCALPHA)
        for i in range(7):
            x = round(i*310-camera*0.35+math.sin(time*0.3+i)*22)
            pg.draw.polygon(light,(160,232,247,16),[(x,85),(x+40,85),(x+155,560),(x+40,560)])
        for y in range(90,600,6):
            pg.draw.rect(light,(4,28,62,round((y-90)/510*48)),(0,y,800,6))
        screen.blit(light,(0,0))

    def draw_ocean(self, game, screen):
        camera = max(0,min(1000,self.swimmer.x-400))
        screen.blit(game.ocean_background,(-round(camera),0))
        self.draw_water_light(screen,game.time,camera)
        game.art.place(screen,'dive-hole',(100-camera,94))
        # A breathing ring connects the surface opening to its interaction area.
        if camera<170:
            exit_center = (round(100-camera),115)
            pg.draw.ellipse(screen,(162,238,239),(exit_center[0]-47,103,94,24),2)
        for i in range(10):
            x = i*190-camera+70
            game.art.place(screen,'ocean-rock' if i%3==0 else 'seaweed',(x,560))
        for i in range(24):
            x = round((i*83+math.sin(game.time+i)*9)%1800-camera)
            y = round(540-(game.time*28+i*37)%425)
            pg.draw.circle(screen,(104,181,211),(x,y),3,1)
        for kind,rect in self.ocean_fish:
            image = game.art.fish(kind,game.time+rect.x*0.01)
            center = (round(rect.centerx-camera),round(rect.centery+math.sin(game.time*2+rect.x)*3))
            screen.blit(image,image.get_rect(center=center))
        image = game.animation.swim_image(game.facing_right)
        screen.blit(image,image.get_rect(center=(round(self.swimmer.x-camera),round(self.swimmer.y+game.animation.swim_bob()))))
        for i in range(5 if game.animation.swim_movement.length_squared() else 2):
            phase = (game.animation.clock*1.4+i/5)%1
            side = -1 if game.facing_right else 1
            x = round(self.swimmer.x-camera+side*(35+phase*40))
            y = round(self.swimmer.y-5-phase*12)
            pg.draw.circle(screen,(136,210,234),(x,y),max(1,round(3*(1-phase))),1)
        for pos,life in self.ocean_rings:
            center = (round(pos[0]-camera),pos[1])
            radius = round(12+(0.65-life)*65)
            pg.draw.circle(screen,(167,241,244),center,radius,2)
            for i in range(8):
                angle = i*math.pi/4
                dot = (round(center[0]+math.cos(angle)*radius),round(center[1]+math.sin(angle)*radius))
                pg.draw.circle(screen,(255,230,141),dot,max(1,round(life*5)))
        return_seconds = self.swimmer.distance_to((100,115))/235+3
        warning = self.oxygen<return_seconds+6
        oxygen_color = (216,110,82) if warning else (51,155,175)
        game.ui.panel(screen,(12,12,776,72))
        game.ui.text(screen,'남극 해양 탐험',(29,23),game.ui.heading)
        game.ui.text(screen,f'물고기 {6-len(self.ocean_fish)}/6 · 먹이 {self.wallet}',(570,27),game.ui.body)
        game.ui.text(screen,f'산소 {max(0,self.oxygen):04.1f}초',(29,57),game.ui.small,oxygen_color)
        pg.draw.rect(screen,(200,222,226),(142,62,400,8),border_radius=4)
        pg.draw.rect(screen,oxygen_color,(142,62,round(400*max(0,min(1,self.oxygen/OXYGEN_DURATION))),8),border_radius=4)
        game.ui.text(screen,f'{game.score} 점',(570,56),game.ui.small)
        near_exit = self.swimmer.distance_to((100,115))<85
        game.ui.panel(screen,(528,95,260,38),dark=True)
        cue = 'E를 눌러 해안으로 귀환' if near_exit else '← ↑ 출구로 돌아가세요' if warning else '왼쪽 위 얼음 구멍이 출구예요'
        game.ui.text(screen,cue,(658,114),game.ui.small,'white',center=True,max_width=236)
        game.ui.panel(screen,(12,526,676,31))
        game.ui.text(screen,'방향키 / WASD 수영 · SPACE 상승 · 출구 근처 E 귀환',(28,532),game.ui.small)
        game.ui.panel(screen,(12,564,776,29))
        game.ui.text(screen,'탐험 경로',(26,570),game.ui.small)
        start,end,y = 130,760,578
        pg.draw.line(screen,(161,206,215),(start,y),(end,y),3)
        pg.draw.circle(screen,(62,150,150),(start+35,y),5)
        for kind,rect in self.ocean_fish:
            pg.draw.circle(screen,(217,160,55) if kind=='gold' else (67,134,171),(start+round(rect.centerx/1800*(end-start)),y),3)
        marker = start+round(self.swimmer.x/1800*(end-start))
        pg.draw.circle(screen,(25,57,76),(marker,y),5)
        pg.draw.circle(screen,'white',(marker,y),2)
        if self.notice_left:
            game.ui.panel(screen,(130,151,540,34),dark=True)
            game.ui.text(screen,self.notice,(400,168),game.ui.small,'white',center=True,max_width=510)
