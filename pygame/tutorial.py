"""Paused first-use instructions and a separate, safe practice stage."""
import math
import pygame as pg

LESSONS = {
    'move': ('눈 위를 걸어 보세요', ['← → 또는 A / D로 이동합니다.', '물고기에 닿으면 점수와 집 꾸미기에 쓸 먹이를 얻습니다.']),
    'jump': ('발판 위로 점프!', ['SPACE / ↑ / W로 점프합니다.', '내려오는 중 발판에 닿으면 착지합니다. 적은 위에서 밟으세요.']),
    'slide': ('배로 미끄러지기', ['↓ / S를 누르며 이동하면 낮은 자세로 빠르게 활주합니다.', '낮은 통로를 지나거나 친구를 가둔 얼음 껍질을 깰 수 있습니다.']),
    'interact': ('친구와 상호작용', ['친구, 깃발, 동굴, 잠수 구멍 근처에서 E를 누르세요.', '친구의 부탁을 해결한 뒤 이글루에 데려다 주면 구조됩니다.']),
    'book': ('탐험 일지 읽기', ['옆길에서 일지를 주우면 TAB으로 기록을 읽을 수 있습니다.', '설명창과 일지 화면이 열린 동안 모든 이동과 제한 시간이 멈춥니다.']),
    'swim': ('산소를 확인하며 수영하세요', ['방향키 / WASD로 수영하고 SPACE로도 위로 올라갑니다.', '산소는 35초입니다. 왼쪽 위 얼음 구멍에서 E로 귀환하세요.', '시간이 부족하면 먼저 돌아오세요. 다음 잠수에서 이어서 탐험합니다.']),
    'escape': ('마지막 빙붕 탈출', ['입구부터 24초 안에 오른쪽 끝까지 건너세요.', '금 간 발판은 흔들린 뒤 무너집니다. 점프와 활주를 활용하세요.', '실패해도 모은 물고기와 구조 기록은 유지됩니다.']),
    'home': ('친구들과 집 꾸미기', ['마지막 이글루 근처에서 E로 둥지, 깃발, 꽃밭을 만듭니다.', '먹이를 사용해도 수집한 물고기 기록과 점수는 줄어들지 않습니다.'])}


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
            game.animation.clock += dt
            movement = pg.Vector2(direction,vertical)
            if movement.length_squared()>1:
                movement.normalize_ip()
            self.swimmer += movement*235*dt
            self.swimmer.x = max(40,min(760,self.swimmer.x))
            self.swimmer.y = max(125,min(490,self.swimmer.y))
            if direction:
                self.right = direction>0
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
            game.ui.text(screen,'출구 E',(70,123),game.ui.small,'white')
            if not self.swim_fish:
                screen.blit(game.art.fish('blue',self.time),(452,338))
            image = game.animation.action_image('swim',self.right)
            screen.blit(image,image.get_rect(center=self.swimmer))
            game.ui.text(screen,'연습 바다 · 산소 제한 없음',(400,520),game.ui.body,'white',center=True)
        else:
            for platform in self.platforms:
                screen.blit(game.platform_texture('snow',platform.size),platform.move(-self.camera,0))
            arch = self.arch.move(-self.camera,0)
            image = game.art.objects['practice-arch']
            screen.blit(image,image.get_rect(midbottom=(arch.centerx,550)))
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
            screen.blit(game.igloo_image,game.igloo_image.get_rect(midbottom=(round(self.home.centerx-self.camera),555)))
            game.art.place(screen,'dive-hole',self.hole.move(-self.camera,0).midbottom)
        game.ui.panel(screen,(12,12,776,73))
        game.ui.text(screen,f'연습 해안 · 튜토리얼 {self.step+1}/6',(29,21),game.ui.heading)
        game.ui.text(screen,self.TASKS[self.step],(29,55),game.ui.body)
        game.ui.panel(screen,(12,563,776,30))
        game.ui.text(screen,'← → 이동 · SPACE 점프 · ↓ 활주 · E 행동 · TAB 일지 · N 튜토리얼 건너뛰기',(28,569),game.ui.small)
        if game.content.book_open:
            game.content.draw_book(game,screen)
