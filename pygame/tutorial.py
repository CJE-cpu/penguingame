"""Paused first-use instructions and a separate, safe practice stage."""
import math
import pygame as pg

LESSONS = {
    'move': ('눈 위를 걸어 보세요', ['← → 또는 A / D로 이동합니다.', '물고기에 닿으면 점수와 집 꾸미기에 쓸 먹이를 얻습니다.']),
    'jump': ('발판 위로 점프!', ['SPACE / ↑ / W로 점프합니다.', '내려오는 중 발판에 닿으면 착지합니다. 적은 위에서 밟으세요.']),
    'slide': ('배로 미끄러지기', ['↓ / S를 누르며 이동하면 낮은 자세로 빠르게 활주합니다.', '낮은 통로를 지나거나 친구를 가둔 얼음 껍질을 깰 수 있습니다.']),
    'interact': ('친구와 상호작용', ['친구, 깃발, 동굴, 잠수 구멍 근처에서 E를 누르세요.', '친구의 부탁을 해결한 뒤 이글루에 데려다 주면 구조됩니다.']),
    'book': ('탐험 일지와 연구 의뢰', ['TAB으로 열고 ← →로 6개 일지와 연구 의뢰 페이지를 넘깁니다.', '일지에는 친구의 위치, 부탁 해결법, 지름길과 위험 요소가 적혀 있습니다.', '의뢰 보상은 이글루 근처에서 E로 받습니다. 읽는 동안 게임 정지!']),
    'swim': ('산소를 확인하며 수영하세요', ['방향키 / WASD로 수영하고 SPACE로도 위로 올라갑니다.', '산소는 35초입니다. 왼쪽 위 얼음 구멍에서 E로 귀환하세요.', '시간이 부족하면 먼저 돌아오세요. 다음 잠수에서 이어서 탐험합니다.']),
    'escape': ('마지막 빙붕 탈출', ['넓어진 빙붕을 32초 안에 건너 오른쪽 보금자리로 가세요.', '발판은 밟고 0.8초 뒤 붕괴합니다. 위쪽 결정은 선택 수집품입니다.', '실패해도 수집과 구조 기록은 유지됩니다. 입구에서 다시 도전하세요.']),
    'home': ('친구들과 집 꾸미기', ['E로 둥지(먹이 5), 깃발(8), 꽃밭(10)을 차례로 만듭니다.', '완료한 연구 의뢰가 있으면 E로 먼저 보상을 받습니다.', '장식과 친구 먹이에 사용해도 물고기 수집 기록과 점수는 유지됩니다.'])}


class Coach:
    def __init__(self):
        self.enabled = False
        self.seen = set()
        self.modal = None

    def explain(self, name):
        if self.enabled and name not in self.seen:
            self.seen.add(name)
            self.modal = LESSONS[name]
            return True
        return False

    def draw(self, game, screen):
        if self.modal is None:
            return
        title, lines = self.modal
        game.ui.veil(screen)
        game.ui.panel(screen,(80,163,640,272))
        game.ui.text(screen,'모험 일시정지',(400,192),game.ui.small,center=True)
        game.ui.text(screen,title,(400,232),game.ui.heading,center=True)
        for index,line in enumerate(lines):
            game.ui.text(screen,line,(400,282+index*29),game.ui.body,center=True)
        game.ui.panel(screen,(221,377,358,40),dark=True)
        game.ui.text(screen,'ENTER / SPACE로 확인 후 연습',(400,397),game.ui.body,'white',center=True)


class TutorialStage:
    STEPS = ['move','jump','slide','interact','book','swim']
    TASKS = ['오른쪽 물고기까지 걸어가세요.', '왼쪽 발판 위 물고기를 향해 점프하세요.',
             '↓를 누르며 낮은 얼음 통로를 지나세요.', '친구 옆에서 E → 오른쪽 이글루로 데려가기',
             'TAB으로 연습 일지를 열고 다시 닫으세요.', '오른쪽 구멍에서 E → 수영해 물고기 획득 → 출구 E']

    def __init__(self, game):
        self.step = 0
        self.player = pg.Rect(55,498,40,52)
        self.x,self.y = float(self.player.x),float(self.player.y)
        self.vy = 0.0
        self.grounded = True
        self.right = True
        self.time = 0.0
        self.camera = 0.0
        self.sliding = False
        self.carrying = False
        self.book_read = False
        self.diving = False
        self.swimmer = pg.Vector2(100,170)
        self.swim_fish = False
        self.finished = False
        self.platforms = [pg.Rect(0,550,1700,50),pg.Rect(320,440,180,24)]
        self.arch = pg.Rect(645,440,180,74)
        self.baby = pg.Rect(940,519,24,31)
        self.home = pg.Rect(1105,490,95,60)
        self.hole = pg.Rect(1450,532,64,18)
        game.coach.explain('move')

    def advance(self, game):
        if self.step<5:
            self.step += 1
            if self.step==4:
                game.content.journals[0]['found'] = True
            game.coach.explain(self.STEPS[self.step])

    def key(self, game, key):
        if game.content.book_open and key in (pg.K_LEFT,pg.K_RIGHT,pg.K_a,pg.K_d):
            game.content.book_page = (game.content.book_page+(1 if key in (pg.K_RIGHT,pg.K_d) else -1))%7
            return
        if self.step==4 and (key == pg.K_TAB or (key == pg.K_e and game.content.book_open)):
            game.content.book_open = not game.content.book_open
            if not game.content.book_open:
                self.book_read = True
                self.advance(game)
        elif key == pg.K_e:
            if self.step==3 and abs(self.player.centerx-self.baby.centerx)<80:
                self.carrying = True
            elif self.step==5:
                if not self.diving and abs(self.player.centerx-self.hole.centerx)<80:
                    self.diving = True
                    self.swimmer.update(100,170)
                elif self.diving and self.swim_fish and self.swimmer.distance_to((100,170))<85:
                    self.diving = False
                    self.finished = True
                    game.coach.modal = ('튜토리얼 완료!', ['기본 조작을 모두 연습했어요. 이제 실제 모험을 시작합니다.', '처음 만나는 도전과 집 꾸미기도 설명창으로 안내합니다.'])

    def update(self, game, dt, direction, jump, slide, vertical):
        if game.content.book_open:
            return
        self.time += dt
        if self.diving:
            movement = pg.Vector2(direction,vertical)
            if movement.length_squared()>1:
                movement.normalize_ip()
            self.swimmer += movement*235*dt
            self.swimmer.x = max(40,min(760,self.swimmer.x))
            self.swimmer.y = max(125,min(490,self.swimmer.y))
            if direction:
                self.right = direction>0
            game.animation.update_swim(dt,movement,self.right)
            if self.swimmer.distance_to((470,350))<40:
                self.swim_fish = True
            return
        was_grounded = self.grounded
        previous_x = self.player.x
        if direction:
            self.right = direction>0
        self.sliding = bool(slide and self.grounded and not jump)
        feet = self.player.midbottom
        standing = self.player.copy()
        standing.height = 52
        standing.midbottom = feet
        if standing.colliderect(self.arch):
            self.sliding = True
            jump = False
        self.player.height = 28 if self.sliding else 52
        self.player.midbottom = feet
        self.y = float(self.player.y)
        previous_bottom = self.player.bottom
        if jump and self.grounded:
            self.vy = -650
        self.x += direction*(365 if self.sliding else 270)*dt
        self.player.x = round(max(0,min(1650,self.x)))
        if self.player.colliderect(self.arch):
            if direction>0:
                self.player.right = self.arch.left
            elif direction<0:
                self.player.left = self.arch.right
        self.x = float(self.player.x)
        self.vy += 1800*dt
        self.y += self.vy*dt
        self.player.y = round(self.y)
        self.grounded = False
        for platform in sorted(self.platforms,key=lambda p:p.y):
            if self.vy>=0 and self.player.right>platform.left and self.player.left<platform.right and previous_bottom<=platform.top<=self.player.bottom:
                self.player.bottom = platform.top
                self.y = float(self.player.y)
                self.vy = 0
                self.grounded = True
                break
        if self.player.top>600:
            self.player.midbottom = (55,550)
            self.x,self.y = map(float,self.player.topleft)
            self.vy = 0
        if self.step==0 and self.player.centerx>260:
            self.advance(game)
        elif self.step==1 and self.player.bottom==440 and self.player.centerx>350:
            self.advance(game)
        elif self.step==2 and self.sliding and self.player.left>self.arch.right:
            self.advance(game)
        elif self.step==3 and self.carrying and self.player.colliderect(self.home):
            self.carrying = False
            self.advance(game)
        self.camera = max(0,min(900,self.player.centerx-400))
        game.animation.update(dt,self.player,self.vy,self.grounded,was_grounded,abs(self.player.x-previous_x))

    def draw(self, game, screen):
        screen.blit(game.scene_backgrounds[0],(-round(self.camera*0.2),0))
        if self.diving:
            screen.blit(game.ocean_background,(0,0))
            game.art.place(screen,'dive-hole',(100,120))
            if not self.swim_fish:
                screen.blit(game.art.fish('blue',self.time),(452,338))
            game.content.draw_water_light(screen,self.time,0)
            image = game.animation.swim_image(self.right)
            screen.blit(image,image.get_rect(center=(self.swimmer.x,self.swimmer.y+game.animation.swim_bob())))
            game.ui.text(screen,'연습 바다 · 산소 제한 없음',(400,520),game.ui.body,'white',center=True)
        else:
            for platform in self.platforms:
                screen.blit(game.platform_texture('snow',platform.size),platform.move(-self.camera,0))
            arch = self.arch.move(-self.camera,0)
            image = game.art.objects['practice-arch']
            game.art.grounded(screen,image,(arch.centerx,550))
            if self.step<=1:
                screen.blit(game.fish_images['blue'],(390-self.camera,410))
                screen.blit(game.fish_images['orange'],(260-self.camera,515))
            image = game.animation.action_image('slide',self.right) if self.sliding else game.animation.image(False,self.right)
            rect = self.player.move(-self.camera,0)
            screen.blit(image,image.get_rect(midbottom=rect.midbottom))
            baby_x = self.player.centerx-45 if self.carrying else self.baby.centerx
            baby_state = ('jump' if self.vy<0 else 'fall') if self.carrying and not self.grounded else 'walk' if self.carrying else 'idle'
            baby_image = game.art.baby(baby_state,self.time,self.right if self.carrying else False)
            screen.blit(baby_image,baby_image.get_rect(midbottom=(round(baby_x-self.camera),self.player.bottom if self.carrying else self.baby.bottom)))
            game.art.grounded(screen,game.igloo_image,(self.home.centerx-self.camera,self.home.bottom))
            game.art.place(screen,'dive-hole',self.hole.move(-self.camera,0).midbottom)
        game.ui.panel(screen,(12,12,776,73))
        game.ui.text(screen,f'연습 해안 · 튜토리얼 {self.step+1}/6',(29,21),game.ui.heading)
        game.ui.text(screen,self.TASKS[self.step],(29,55),game.ui.body)
        game.ui.panel(screen,(12,563,776,30))
        game.ui.text(screen,'← → 이동 · SPACE 점프 · ↓ 활주 · E 행동 · TAB 일지 · N 튜토리얼 건너뛰기',(28,569),game.ui.small)
        if game.content.book_open:
            game.content.draw_book(game,screen)
