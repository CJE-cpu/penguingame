"""Animated ending sequence shown after a successful expedition."""
import math
import pygame as pg

ENDING_NAMES = ('첫 번째 엔딩 · 홀로 귀환',
                '두 번째 엔딩 · 풍요로운 귀환',
                '세 번째 엔딩 · 모두 함께',
                '시크릿 엔딩 · 남극의 보물')


class EndingSequence:
    def __init__(self, ending_type=3):
        self.ending_type = max(1, min(4, ending_type))
        self.title = ENDING_NAMES[self.ending_type-1]
        self.page = 0
        self.time = 0.0
        self.finished = False
        self.choice = 0

    def update(self, dt):
        self.time += dt

    def advance(self):
        self.finished = True
        return ('explore', 'restart', 'records')[self.choice]

    def back(self):
        self.choice = (self.choice-1) % 3

    def forward(self):
        self.choice = (self.choice+1) % 3

    def buttons(self):
        return [pg.Rect(190+index*143, 554, 132, 34) for index in range(3)]

    def _fade(self, screen):
        age = min(1.0, self.time/0.55)
        veil = pg.Surface(screen.get_size(), pg.SRCALPHA)
        veil.fill((8, 28, 48, round(210*(1-age))))
        screen.blit(veil, (0, 0))

    def _backdrop(self, game, screen, index):
        """Draw one ending-specific panorama with a subtle cinematic finish."""
        screen.blit(game.ending_backgrounds[index], (0, 0))
        vignette = pg.Surface(screen.get_size(), pg.SRCALPHA)
        pg.draw.rect(vignette, (3, 18, 38, 72), (0, 0, 800, 600), 22)
        screen.blit(vignette, (0, 0))
        # Sparse foreground snow gives the still paintings gentle motion.
        count = 14 if game.quality == 'performance' else 24
        for index in range(count):
            x = round((index*97+self.time*(11+index%3*4))%840)-20
            y = round((index*53+self.time*(19+index%4*3))%420)+4
            shade = 190+index%3*20
            pg.draw.circle(screen, (shade, shade+10, 255), (x, y),
                           1+(index%7==0))

    def _challenge_badges(self, game, screen):
        """Show optional run goals without changing the ending score."""
        ui = game.ui
        goals = (('무피격', game.hits == 0),
                 ('무추락', game.falls == 0),
                 ('5분', game.time <= 300))
        ui.panel(screen, (178, 18, 444, 50))
        ui.text(screen, '탐험 도전', (195, 33), ui.small)
        for index, (label, earned) in enumerate(goals):
            rect = pg.Rect(274 + index*112, 28, 102, 30)
            pg.draw.rect(screen, (53, 118, 139) if earned else (191, 207, 212),
                         rect, border_radius=8)
            ui.text(screen, label + (' 성공' if earned else ' 미달'), rect.center,
                    ui.small, 'white' if earned else (88, 108, 117), center=True)

    def _caption(self, game, screen, title, lines):
        ui = game.ui
        ui.panel(screen, (64, 430, 672, 118), dark=True)
        ui.text(screen, title, (400, 458), ui.heading, 'white', center=True)
        for index, line in enumerate(lines):
            ui.text(screen, line, (400, 490+index*22), ui.small,
                    (224, 246, 251), center=True, max_width=620)
        labels = ('수집 계속', '새 모험', '기록 보기')
        for index, (label, rect) in enumerate(zip(labels, self.buttons())):
            ui.panel(screen, rect, dark=index == self.choice)
            ui.text(screen, label, rect.center, ui.small,
                    'white' if index == self.choice else (25,57,76), center=True)

    def _home_scene(self, game, screen):
        self._backdrop(game, screen, 0)
        progress = min(1.0, self.time/4.0)
        x = round(100+progress*385)
        bounce = round(abs(math.sin(self.time*6))*4)
        frames = game.animation.cycles['walk']
        penguin = frames[int(self.time/0.145)%len(frames)]
        screen.blit(penguin, penguin.get_rect(midbottom=(x, 420-bounce)))
        if self.ending_type >= 2:
            for index in range(3):
                fish = game.art.fish(('orange', 'blue', 'gold')[index], self.time+index)
                screen.blit(fish, fish.get_rect(center=(x+48+index*27, 392-index*5)))
        if self.ending_type == 4:
            treasure = pg.transform.smoothscale(game.chest_image, (43, 36))
            screen.blit(treasure, treasure.get_rect(midbottom=(x+78, 420)))
        for index in range(game.rescued):
            bx = x-52-index*43
            by = 420-round(abs(math.sin(self.time*6-index*.8))*3)
            baby = game.art.baby('walk', self.time+index*.2, True)
            screen.blit(baby, baby.get_rect(midbottom=(bx, by)))
        lines = (
            ('긴 여행 끝에 마지막 이글루를 발견했습니다.', '아직 만나지 못한 친구와 물고기는 다음 탐험을 기다립니다.'),
            ('모든 물고기를 품에 안고 마지막 이글루로 돌아왔습니다.', '풍성한 먹이는 새로운 여정을 준비할 힘이 됩니다.'),
            ('긴 빙붕을 건너 펭귄과 친구들이 함께 집으로 돌아갑니다.', '이제 누구도 남극에 혼자 남지 않았어요.'),
            ('친구들과 보물을 싣고 황금빛 발자국을 남기며 돌아옵니다.', '남극의 오래된 비밀이 마침내 세상에 모습을 드러냈습니다.'))
        self._caption(game, screen, self.title, lines[self.ending_type-1])

    def _feast_scene(self, game, screen):
        self._backdrop(game, screen, 3 if self.ending_type == 4 else 1)
        glow = pg.Surface((800, 600), pg.SRCALPHA)
        for radius in range(180, 20, -20):
            pg.draw.circle(glow, (255, 210, 105, 5), (400, 285), radius)
        if self.ending_type == 4:
            pulse = 28+round(math.sin(self.time*3)*5)
            pg.draw.circle(glow, (255, 230, 126, 72), (548, 357), pulse, 3)
        screen.blit(glow, (0, 0))
        frames = game.animation.cycles['idle']
        adult = frames[int(self.time/0.35)%len(frames)]
        adult_y = 382 if self.ending_type == 4 else 370
        screen.blit(adult, adult.get_rect(midbottom=(400, adult_y)))
        companion_x = (275, 325, 475)[:game.rescued]
        for index, x in enumerate(companion_x):
            state = 'jump' if int(self.time*2+index)%2 else 'idle'
            baby = game.art.baby(state, self.time+index*.3, index == 2)
            screen.blit(baby, baby.get_rect(midbottom=(x, adult_y+3)))
        fish_count = min(4, game.total-len(game.fish))
        for index, x in enumerate((305, 365, 435, 495)[:fish_count]):
            fish = game.art.fish(('orange', 'blue', 'gold')[index%3], self.time+index)
            screen.blit(fish, fish.get_rect(center=(x, 300+round(math.sin(self.time*3+index)*4))))
        if self.ending_type == 4:
            game.art.grounded(screen, game.chest_image, (548, adult_y))
        lines = (
            ('작은 이글루에 조용한 저녁이 찾아왔습니다.', '빈자리를 기억한 펭귄은 다시 길을 나설 준비를 합니다.'),
            ('모은 물고기로 식탁을 채우자 긴 여행의 피로가 녹았습니다.', '다음에는 이 풍요를 함께 나눌 친구를 찾아야 합니다.'),
            ('모은 물고기를 나누고 탐험 이야기를 들려주는 축제가 열렸습니다.', '보금자리는 친구들의 웃음으로 더 따뜻해졌어요.'),
            ('동굴의 보물이 이글루를 밝히고 모두를 위한 축제가 열렸습니다.', '황금빛 결정에는 오래된 남극 탐험가의 지도가 숨어 있었습니다.'))
        self._caption(game, screen, self.title, lines[self.ending_type-1])

    def _night_scene(self, game, screen):
        self._backdrop(game, screen, 2)
        for index in range(55):
            x = (index*149+37)%800
            y = 35+(index*71)%335
            radius = 1+(index%3==0)
            shade = 175+round(70*(math.sin(self.time*2+index)+1)/2)
            pg.draw.circle(screen, (shade, shade, 220), (x, y), radius)
        group_size = 1+game.rescued
        positions = (335, 380, 420, 462)[:group_size]
        for index, x in enumerate(positions):
            image = game.penguin_right if index == 0 else game.art.baby('idle', self.time+index)
            size = (42, 56) if index == 0 else (25, 32)
            image = pg.transform.smoothscale(image, size)
            screen.blit(image, image.get_rect(midbottom=(x, 440)))
        lines = (
            ('오로라 아래에서 오늘의 짧은 휴식을 기록했습니다.', '내일은 남겨 둔 물고기와 친구를 찾아 다시 출발합니다.'),
            ('별빛 아래 물고기 떼의 길을 지도에 표시했습니다.', '다음 여행에는 함께 웃을 친구를 찾기로 했습니다.'),
            ('밤하늘의 오로라 아래, 네 펭귄은 다음 모험을 약속했습니다.', '남극의 작은 발자국은 오래도록 이어질 거예요.'),
            ('보물의 빛이 오로라와 만나 남극 하늘에 새로운 길을 그렸습니다.', '네 펭귄의 모험은 오래도록 전설로 전해질 거예요.'))
        self._caption(game, screen, self.title, lines[self.ending_type-1])

    def draw(self, game, screen):
        if self.ending_type == 1:
            self._home_scene(game, screen)
        elif self.ending_type in (2, 4):
            self._feast_scene(game, screen)
        else:
            self._night_scene(game, screen)
        self._challenge_badges(game, screen)
        self._fade(screen)
