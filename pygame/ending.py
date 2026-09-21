"""Animated ending sequence shown after a successful expedition."""
import math
import pygame as pg

ENDING_NAMES = ('첫 번째 엔딩 · 홀로 귀환',
                '두 번째 엔딩 · 풍요로운 귀환',
                '세 번째 엔딩 · 모두 함께',
                '시크릿 엔딩 · 남극의 보물')


class EndingSequence:
    STORY_TITLES = (
        ('긴 여정의 끝', '조용한 보금자리', '다시 떠날 약속', ENDING_NAMES[0]),
        ('가득 찬 배낭', '풍성한 식탁', '다음 여행의 지도', ENDING_NAMES[1]),
        ('함께 돌아가는 길', '따뜻한 보금자리', '남극의 밤', ENDING_NAMES[2]),
        ('황금빛 귀환', '보물이 밝힌 집', '전설이 된 밤', ENDING_NAMES[3]))

    def __init__(self, ending_type=3):
        self.ending_type = max(1, min(4, ending_type))
        self.TITLES = self.STORY_TITLES[self.ending_type-1]
        self.page = 0
        self.time = 0.0
        self.finished = False

    def update(self, dt):
        self.time += dt

    def advance(self):
        if self.page < len(self.TITLES)-1:
            self.page += 1
            self.time = 0.0
            return False
        self.finished = True
        return True

    def back(self):
        if self.page:
            self.page -= 1
            self.time = 0.0

    def _fade(self, screen):
        age = min(1.0, self.time/0.55)
        veil = pg.Surface(screen.get_size(), pg.SRCALPHA)
        veil.fill((8, 28, 48, round(210*(1-age))))
        screen.blit(veil, (0, 0))

    def _caption(self, game, screen, title, lines):
        ui = game.ui
        ui.panel(screen, (64, 430, 672, 118), dark=True)
        ui.text(screen, title, (400, 458), ui.heading, 'white', center=True)
        for index, line in enumerate(lines):
            ui.text(screen, line, (400, 490+index*22), ui.small,
                    (224, 246, 251), center=True, max_width=620)
        ui.panel(screen, (248, 556, 304, 30), dark=True)
        ui.text(screen, f'{self.page+1}/{len(self.TITLES)}  ·  ENTER 다음  ·  ← 이전',
                (400, 571), ui.small, 'white', center=True)

    def _home_scene(self, game, screen):
        screen.blit(game.scene_backgrounds[5], (0, 0))
        pg.draw.rect(screen, (219, 243, 248), (0, 420, 800, 180))
        game.art.grounded(screen, game.igloo_image, (655, 422))
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
        self._caption(game, screen, self.TITLES[0], lines[self.ending_type-1])

    def _feast_scene(self, game, screen):
        screen.blit(game.scene_backgrounds[5], (0, 0))
        glow = pg.Surface((800, 600), pg.SRCALPHA)
        for radius in range(180, 20, -20):
            pg.draw.circle(glow, (255, 210, 105, 5), (400, 285), radius)
        screen.blit(glow, (0, 0))
        game.art.grounded(screen, game.igloo_image, (400, 365))
        frames = game.animation.cycles['idle']
        adult = frames[int(self.time/0.35)%len(frames)]
        screen.blit(adult, adult.get_rect(midbottom=(400, 370)))
        companion_x = (275, 325, 475)[:game.rescued]
        for index, x in enumerate(companion_x):
            state = 'jump' if int(self.time*2+index)%2 else 'idle'
            baby = game.art.baby(state, self.time+index*.3, index == 2)
            screen.blit(baby, baby.get_rect(midbottom=(x, 373)))
        fish_count = min(4, game.total-len(game.fish))
        for index, x in enumerate((305, 365, 435, 495)[:fish_count]):
            fish = game.art.fish(('orange', 'blue', 'gold')[index%3], self.time+index)
            screen.blit(fish, fish.get_rect(center=(x, 300+round(math.sin(self.time*3+index)*4))))
        if self.ending_type == 4:
            game.art.grounded(screen, game.chest_image, (548, 370))
        lines = (
            ('작은 이글루에 조용한 저녁이 찾아왔습니다.', '빈자리를 기억한 펭귄은 다시 길을 나설 준비를 합니다.'),
            ('모은 물고기로 식탁을 채우자 긴 여행의 피로가 녹았습니다.', '다음에는 이 풍요를 함께 나눌 친구를 찾아야 합니다.'),
            ('모은 물고기를 나누고 탐험 이야기를 들려주는 축제가 열렸습니다.', '보금자리는 친구들의 웃음으로 더 따뜻해졌어요.'),
            ('동굴의 보물이 이글루를 밝히고 모두를 위한 축제가 열렸습니다.', '황금빛 결정에는 오래된 남극 탐험가의 지도가 숨어 있었습니다.'))
        self._caption(game, screen, self.TITLES[1], lines[self.ending_type-1])

    def _night_scene(self, game, screen):
        screen.fill((8, 24, 54))
        for index in range(55):
            x = (index*149+37)%800
            y = 35+(index*71)%335
            radius = 1+(index%3==0)
            shade = 175+round(70*(math.sin(self.time*2+index)+1)/2)
            pg.draw.circle(screen, (shade, shade, 220), (x, y), radius)
        aurora = pg.Surface((800, 380), pg.SRCALPHA)
        for band, color in enumerate(((89, 240, 186, 85), (91, 190, 255, 65), (188, 126, 255, 50))):
            points = []
            for x in range(-20, 841, 20):
                y = 100+band*35+round(math.sin(x*.012+self.time*.45+band)*34)
                points.append((x, y))
            pg.draw.lines(aurora, color, False, points, 18-band*3)
        screen.blit(aurora, (0, 0))
        pg.draw.polygon(screen, (26, 57, 81), [(0, 430), (130, 315), (240, 430),
                                                (390, 285), (560, 430), (690, 330),
                                                (800, 425), (800, 600), (0, 600)])
        group_size = 1+game.rescued
        positions = (335, 380, 420, 462)[:group_size]
        for index, x in enumerate(positions):
            image = game.penguin_right if index == 0 else game.art.baby('idle', self.time+index)
            size = (42, 56) if index == 0 else (25, 32)
            image = pg.transform.smoothscale(image, size)
            screen.blit(image, image.get_rect(midbottom=(x, 432)))
        lines = (
            ('오로라 아래에서 오늘의 짧은 휴식을 기록했습니다.', '내일은 남겨 둔 물고기와 친구를 찾아 다시 출발합니다.'),
            ('별빛 아래 물고기 떼의 길을 지도에 표시했습니다.', '다음 여행에는 함께 웃을 친구를 찾기로 했습니다.'),
            ('밤하늘의 오로라 아래, 네 펭귄은 다음 모험을 약속했습니다.', '남극의 작은 발자국은 오래도록 이어질 거예요.'),
            ('보물의 빛이 오로라와 만나 남극 하늘에 새로운 길을 그렸습니다.', '네 펭귄의 모험은 오래도록 전설로 전해질 거예요.'))
        self._caption(game, screen, self.TITLES[2], lines[self.ending_type-1])

    def _record_scene(self, game, screen):
        screen.blit(game.scene_backgrounds[5], (0, 0))
        game.ui.veil(screen)
        ui = game.ui
        ui.panel(screen, (105, 70, 590, 430))
        ui.text(screen, self.TITLES[3], (400, 112), ui.title, center=True)
        ui.text(screen, 'LITTLE FEET, BIG ADVENTURES', (400, 157), ui.small,
                (53, 116, 137), center=True)
        elapsed = max(0, round(game.time))
        rows = [
            ('달성한 엔딩', f'{self.ending_type}/4'),
            ('최종 점수', f'{game.score}점'),
            ('모은 물고기', f'{game.total-len(game.fish)}/{game.total}'),
            ('구조한 친구', f'{game.rescued}/3'),
            ('동굴 보물', f'{sum(c["treasure"] for c in game.caves)}/{len(game.caves)}'),
        ]
        for index, (label, value) in enumerate(rows):
            y = 205+index*48
            ui.text(screen, label, (190, y), ui.body, (67, 99, 117))
            if value is None:
                ui.life_icons(screen, game, (558, y+10), (22, 28), 34)
            else:
                ui.text(screen, value, (610, y), ui.heading, (36, 101, 127), center=True)
            pg.draw.line(screen, (190, 222, 229), (190, y+34), (610, y+34))
        ui.panel(screen, (190, 445, 420, 42), dark=True)
        ui.text(screen, 'ENTER 자유 탐험으로 돌아가기', (400, 466), ui.body,
                'white', center=True)
        ui.text(screen, '4/4  ·  ← 이전', (400, 526), ui.small,
                (44, 83, 103), center=True)

    def draw(self, game, screen):
        if self.page == 0:
            self._home_scene(game, screen)
        elif self.page == 1:
            self._feast_scene(game, screen)
        elif self.page == 2:
            self._night_scene(game, screen)
        else:
            self._record_scene(game, screen)
        self._fade(screen)
