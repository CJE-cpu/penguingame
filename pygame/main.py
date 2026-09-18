"""Antarctic penguin platformer. Arrows/A/D: move; Space: jump; R: restart."""
from pathlib import Path
import math
import pygame as pg

WIDTH, HEIGHT = 800, 600
REGION_WIDTH = 1200
REGIONS = [('눈 덮인 해안', (109, 192, 226)), ('미끄러운 빙하', (80, 211, 239)),
           ('얼음 동굴', (106, 129, 179)), ('눈보라 고원', (159, 183, 202)),
           ('갈라진 빙붕', (148, 183, 230)), ('펭귄의 보금자리', (132, 206, 183))]
WORLD_WIDTH = REGION_WIDTH * len(REGIONS)
SCENES = ['snow-coast', 'glacier-canyon', 'ice-cave', 'blizzard-plateau', 'fractured-shelf', 'sunset-home']
# Each region has a different silhouette and optional upper routes.
MAP_LAYOUTS = [
    ([(0,550,360), (430,550,370), (870,550,330)],
     [(180,450,190), (370,360,170), (550,270,160), (735,360,150), (900,450,160)]),
    ([(0,550,280), (360,530,220), (660,550,210), (950,550,250)],
     [(160,450,140), (330,360,150), (510,280,190), (730,370,140), (910,455,150)]),
    ([(0,550,1200)],
     [(200,450,170), (380,355,180), (580,265,190), (380,175,190), (800,355,180), (990,450,150)]),
    ([(0,550,310), (370,520,250), (690,490,230), (995,550,205)],
     [(160,450,180), (350,365,200), (575,280,180), (780,205,190)]),
    ([(0,550,250), (315,550,230), (610,550,240), (925,550,275)],
     [(180,460,150), (345,390,150), (510,320,160), (700,390,150), (865,460,160)]),
    ([(0,550,350), (420,550,780)],
     [(190,450,200), (395,365,160), (575,280,180), (785,365,160), (975,450,180)])]
FISH_TYPES = {'orange': ('orange-fish.png', (255, 255, 255), 10),
              'blue': ('blue-fish.png', (255, 255, 255), 25),
              'gold': ('gold-fish.png', (255, 255, 255), 50)}
DATA = Path(__file__).resolve().parent / 'data'
GRAVITY = 1800
MOVE_SPEED = 270
JUMP_SPEED = -650
ITEM_DURATION = 8.0
ENEMY_POINTS = 30
ITEM_STYLE = {'grow': ((126, 224, 126), '+', 'BIG'),
              'speed': ((255, 212, 92), '>>', 'FAST'),
              'reverse': ((221, 142, 255), '<>', 'REVERSE')}


def load_image(name, size=None, keep_aspect=False):
    image = pg.image.load(str(DATA / name)).convert_alpha()
    if size and keep_aspect:
        # Remove transparent padding before fitting the visible sprite.
        image = image.subsurface(image.get_bounding_rect(min_alpha=128)).copy()
        ratio = min(size[0] / image.get_width(), size[1] / image.get_height())
        fitted_size = (max(1, round(image.get_width() * ratio)),
                       max(1, round(image.get_height() * ratio)))
        fitted = pg.transform.scale(image, fitted_size)
        canvas = pg.Surface(size, pg.SRCALPHA)
        canvas.blit(fitted, fitted.get_rect(midbottom=(size[0] // 2, size[1])))
        return canvas
    return pg.transform.scale(image, size) if size else image


class Enemy:
    """A crab that patrols its platform without falling off the edge."""
    def __init__(self, platform, speed):
        self.rect = pg.Rect(platform.centerx - 22, platform.top - 30, 44, 30)
        self.x = float(self.rect.x)
        self.left, self.right = platform.left + 8, platform.right - 8
        self.speed = speed

    def update(self, dt):
        self.x += self.speed * dt
        if self.x <= self.left:
            self.x = float(self.left)
            self.speed = abs(self.speed)
        elif self.x >= self.right - self.rect.width:
            self.x = float(self.right - self.rect.width)
            self.speed = -abs(self.speed)
        self.rect.x = round(self.x)

    def draw(self, screen, camera_x, image):
        rect = self.rect.move(-camera_x, 0)
        screen.blit(image if self.speed < 0 else pg.transform.flip(image, True, False), rect)


class Game:
    def __init__(self):
        self.background = load_image('antarctica-background.png', (WIDTH, HEIGHT))
        self.scene_backgrounds = [load_image('scene-' + scene + '.png', (WIDTH, HEIGHT)) for scene in SCENES]
        self.penguin_left = load_image('penguin-adult-left.png', (40, 52), keep_aspect=True)
        self.penguin_right = pg.transform.flip(self.penguin_left, True, False)
        self.big_penguin_left = load_image('penguin-adult-left.png', (60, 78), keep_aspect=True)
        self.big_penguin_right = pg.transform.flip(self.big_penguin_left, True, False)
        self.fish_images = {}
        for kind, (filename, tint, points) in FISH_TYPES.items():
            image = load_image(filename, (36, 24), keep_aspect=True)
            self.fish_images[kind] = image
        self.font = pg.font.Font(None, 30)
        self.big_font = pg.font.Font(None, 64)
        korean_font = pg.font.match_font('malgungothic, 맑은 고딕, nanumgothic')
        self.intro_font = pg.font.Font(korean_font, 21)
        self.intro_title_font = pg.font.Font(korean_font, 36)
        self.baby_image = load_image('penguin-baby-left.png', (24, 31), keep_aspect=True)
        self.crab_image = load_image('crab-enemy.png', (44, 30), keep_aspect=True)
        self.igloo_image = load_image('igloo-checkpoint.png', (112, 85), keep_aspect=True)
        self.cave_image = load_image('ice-cave-entrance.png', (180, 135), keep_aspect=True)
        self.chest_image = load_image('golden-treasure-chest.png', (36, 30), keep_aspect=True)
        self.item_images = {kind: load_image(filename + '-potion.png', (30, 36), keep_aspect=True)
                            for kind, filename in [('grow', 'growth'), ('speed', 'speed'), ('reverse', 'reverse')]}
        self.platform_images = {kind: load_image(filename + '-platform-tile.png', (80, 30))
                                for kind, filename in [('snow', 'snow'), ('ice', 'smooth-ice'), ('crumble', 'cracked-ice')]}
        self.platforms = []
        self.platform_kinds = {}
        self.grounds = []
        self.region_grounds = []
        self.region_ledges = []
        for region, (ground_layout, ledge_layout) in enumerate(MAP_LAYOUTS):
            offset = region * REGION_WIDTH
            grounds = [pg.Rect(offset+x, y, w, HEIGHT-y) for x,y,w in ground_layout]
            ledges = [pg.Rect(offset+x, y, w, 24) for x,y,w in ledge_layout]
            self.region_grounds.append(grounds)
            self.region_ledges.append(ledges)
            self.grounds.extend(grounds)
            for rect in grounds + ledges:
                self.platforms.append(rect)
                kind = 'ice' if region in (1, 3) else 'snow'
                if region == 4 and rect in ledges:
                    kind = 'crumble'
                self.platform_kinds[tuple(rect)] = kind
        self.ground_keys = {tuple(p) for p in self.grounds}
        self.reset()

    def reset(self):
        self.player = pg.Rect(55, 498, 40, 52)
        self.x, self.y = float(self.player.x), float(self.player.y)
        self.velocity_y = 0.0
        self.velocity_x = 0.0
        self.surface_kind = 'snow'
        self.on_ground = True
        self.facing_right = True
        self.fish = []
        for region in range(len(REGIONS)):
            offset = region * REGION_WIDTH
            grounds = self.region_grounds[region]
            for platform, shift in [(grounds[0], 35), (grounds[-1], -35)]:
                self.fish.append(('orange', pg.Rect(platform.centerx + shift - 18, platform.top - 35, 36, 24)))
            ledges = self.region_ledges[region]
            for kind, platform in [('blue', ledges[0]), ('blue', ledges[1]), ('gold', min(ledges, key=lambda p:p.y))]:
                self.fish.append((kind, pg.Rect(platform.centerx - 18, platform.top - 35, 36, 24)))
        self.total = len(self.fish)
        self.score = 0
        self.max_score = sum(FISH_TYPES[kind][2] for kind, rect in self.fish)
        self.enemies = [Enemy(self.region_grounds[region][-1], 65 + region * 8)
                        for region in range(len(REGIONS))]
        self.max_score += len(self.enemies) * ENEMY_POINTS
        self.defeated = 0
        self.hits = 0
        self.invincible = 0.0
        self.camera_x = 0
        self.started = False
        self.falls = 0
        self.won = False
        self.time = 0.0
        self.effects = {kind: 0.0 for kind in ITEM_STYLE}
        self.items = []
        for region in range(len(REGIONS)):
            for kind, platform, shift in [('grow', self.region_grounds[region][0], 120),
                                          ('speed', self.region_ledges[region][0], 35),
                                          ('reverse', self.region_grounds[region][-1], 65)]:
                self.items.append((kind, pg.Rect(platform.x + shift, platform.top - 36, 30, 36)))
        self.checkpoints = [pg.Rect(i * REGION_WIDTH + 30, 490, 95, 60)
                            for i in range(len(REGIONS))]
        self.checkpoint_index = 0
        self.spawn = (55, 498)
        self.crumbles = {}  # key -> (elapsed since stepped on, time left hidden)
        self.caves = [{'rect': pg.Rect(self.region_grounds[i][-1].right - 210, 420, 180, 130),
                       'found': False, 'treasure': False} for i in (2, 4)]
        self.babies = []
        for region in (1, 3, 5):
            platform = min(self.region_ledges[region], key=lambda p:p.y)
            self.babies.append({'rect': pg.Rect(platform.right - 40, platform.top - 31, 24, 31),
                                'rescued': False})
        self.carried_baby = None
        self.rescued = 0
        self.max_score += len(self.babies) * 100 + len(self.caves) * 100

    def active_platforms(self):
        return [p for p in self.platforms if self.crumbles.get(tuple(p), (0, 0))[1] <= 0]

    def update_adventure(self, dt):
        for key, (elapsed, hidden) in list(self.crumbles.items()):
            if hidden > 0:
                hidden = max(0, hidden - dt)
                if not hidden:
                    # Wait until the player leaves before restoring solid ice.
                    if self.player.colliderect(pg.Rect(key)):
                        self.crumbles[key] = (elapsed, 0.1)
                        continue
                    del self.crumbles[key]
                    continue
            else:
                elapsed += dt
                if elapsed >= 0.8:
                    hidden = 4.0
            self.crumbles[key] = (elapsed, hidden)
        for index, checkpoint in enumerate(self.checkpoints):
            if self.player.colliderect(checkpoint):
                self.checkpoint_index = index
                self.spawn = (checkpoint.x + 25, 498)
                if self.carried_baby is not None:
                    self.babies[self.carried_baby]['rescued'] = True
                    self.carried_baby = None
                    self.rescued += 1
                    self.score += 100
        for index, baby in enumerate(self.babies):
            if (not baby['rescued'] and self.carried_baby is None
                    and self.player.colliderect(baby['rect'])):
                self.carried_baby = index
        for cave in self.caves:
            if self.player.colliderect(cave['rect']):
                cave['found'] = True
                chest = pg.Rect(cave['rect'].right - 45, 515, 30, 30)
                if not cave['treasure'] and self.player.colliderect(chest):
                    cave['treasure'] = True
                    self.score += 100

    def respawn(self, hit=False):
        self.effects = {kind: 0.0 for kind in ITEM_STYLE}
        self.player.size = (40, 52)
        self.player.topleft = self.spawn
        self.x, self.y = map(float, self.player.topleft)
        self.velocity_y = 0.0
        self.velocity_x = 0.0
        self.surface_kind = 'snow'
        self.carried_baby = None
        self.crumbles.clear()
        self.on_ground = True
        if hit:
            self.hits += 1
        else:
            self.falls += 1
        self.invincible = 2.0
        self.camera_x = max(0, min(WORLD_WIDTH - WIDTH, self.player.centerx - WIDTH // 2))

    def update(self, dt, direction=0, jump=False):
        if not self.started:
            return
        self.time += dt
        if self.won:
            return
        self.invincible = max(0.0, self.invincible - dt)
        self.update_adventure(dt)
        previous_bottom = self.player.bottom
        for enemy in self.enemies:
            enemy.update(dt)
        for kind in self.effects:
            self.effects[kind] = max(0.0, self.effects[kind] - dt)
        if self.effects['reverse']:
            direction = -direction
        speed = MOVE_SPEED * (1.6 if self.effects['speed'] else 1.0)
        if jump and self.on_ground:
            self.velocity_y = JUMP_SPEED
            self.on_ground = False
        if direction:
            self.facing_right = direction > 0
        if self.surface_kind == 'ice':
            if direction:
                change = 650 * dt
                target = direction * speed
                self.velocity_x += max(-change, min(change, target - self.velocity_x))
            else:
                self.velocity_x *= math.exp(-1.5 * dt)
        else:
            self.velocity_x = direction * speed
        wind = -75 if 3 * REGION_WIDTH <= self.player.centerx < 4 * REGION_WIDTH else 0
        movement = self.velocity_x + wind
        self.x += movement * dt
        self.player.x = round(self.x)
        for platform in self.grounds:
            if self.player.colliderect(platform):
                if movement > 0:
                    self.player.right = platform.left
                elif movement < 0:
                    self.player.left = platform.right
                self.x = float(self.player.x)
                self.velocity_x = 0
        self.player.x = max(0, min(WORLD_WIDTH - self.player.width, self.player.x))
        if self.player.x != round(self.x):
            self.x = float(self.player.x)
        self.velocity_y += GRAVITY * dt
        self.y += self.velocity_y * dt
        self.player.y = round(self.y)
        self.on_ground = False
        landings = []
        for platform in self.active_platforms():
            overlap_x = self.player.right > platform.left and self.player.left < platform.right
            if (self.velocity_y >= 0 and overlap_x
                    and previous_bottom <= platform.top <= self.player.bottom):
                landings.append(platform)
            elif (tuple(platform) in self.ground_keys and self.player.colliderect(platform)
                  and self.velocity_y < 0):
                    self.player.top = platform.bottom
                    self.y = float(self.player.y)
                    self.velocity_y = 0.0
        if landings:
            platform = min(landings, key=lambda p:p.top)
            self.player.bottom = platform.top
            self.on_ground = True
            self.surface_kind = self.platform_kinds[tuple(platform)]
            if self.surface_kind == 'crumble':
                self.crumbles.setdefault(tuple(platform), (0.0, 0.0))
            self.y = float(self.player.y)
            self.velocity_y = 0.0
        # Descending from above is a stomp; side and upward contact cause damage.
        for enemy in list(self.enemies):
            if not self.player.colliderect(enemy.rect):
                continue
            if self.effects['grow'] or (self.velocity_y > 0 and previous_bottom <= enemy.rect.top + 3):
                self.enemies.remove(enemy)
                self.score += ENEMY_POINTS
                self.defeated += 1
                if not self.effects['grow']:
                    self.player.bottom = enemy.rect.top
                    self.y = float(self.player.y)
                    self.velocity_y = -420
                    self.on_ground = False
            elif not self.invincible:
                self.respawn(hit=True)
                return
        remaining_fish = []
        for kind, rect in self.fish:
            if self.player.colliderect(rect):
                self.score += FISH_TYPES[kind][2]
            else:
                remaining_fish.append((kind, rect))
        self.fish = remaining_fish
        remaining_items = []
        for kind, rect in self.items:
            if not self.player.colliderect(rect):
                remaining_items.append((kind, rect))
            else:
                self.effects[kind] = ITEM_DURATION
        self.items = remaining_items
        self.update_adventure(0)
        if not self.fish and self.rescued == len(self.babies):
            self.won = True
        if self.player.top > HEIGHT:
            self.respawn()
        self.camera_x = max(0, min(WORLD_WIDTH - WIDTH, self.player.centerx - WIDTH // 2))

    def draw(self, screen):
        if not self.started:
            self.draw_intro(screen)
            return
        region = min(len(REGIONS) - 1, self.player.centerx // REGION_WIDTH)
        background = self.scene_backgrounds[region]
        background_x = -int(self.camera_x * 0.2) % WIDTH
        screen.blit(background, (background_x - WIDTH, 0))
        screen.blit(background, (background_x, 0))
        # Show water in the ground gaps so falls are visually clear.
        pg.draw.rect(screen, (24, 88, 130), (0, 550, WIDTH, 50))
        self.draw_adventure(screen)
        for platform in self.active_platforms():
            rect = platform.move(-self.camera_x, 0)
            kind = self.platform_kinds[tuple(platform)]
            tile = self.platform_images[kind]
            clip = screen.get_clip()
            screen.set_clip(rect.clip(screen.get_rect()))
            for y in range(rect.y, rect.bottom, tile.get_height()):
                for x in range(rect.x, rect.right, tile.get_width()):
                    screen.blit(tile, (x, y))
            screen.set_clip(clip)
            if kind == 'crumble' and tuple(platform) in self.crumbles:
                progress = min(1, self.crumbles[tuple(platform)][0] / 0.8)
                pg.draw.rect(screen, (245, 92, 125), (rect.x, rect.y-4, int(rect.width*progress), 3))
        for index, (kind, fish) in enumerate(self.fish):
            bob = round(math.sin(self.time * 4 + index) * 3)
            screen.blit(self.fish_images[kind], fish.move(-self.camera_x, bob))
        for enemy in self.enemies:
            enemy.draw(screen, self.camera_x, self.crab_image)
        for kind, rect in self.items:
            rect = rect.move(-self.camera_x, 0)
            screen.blit(self.item_images[kind], rect)
        if self.effects['grow']:
            image = self.big_penguin_right if self.facing_right else self.big_penguin_left
        else:
            image = self.penguin_right if self.facing_right else self.penguin_left
        if not self.invincible or int(self.time * 10) % 2 == 0:
            rect = self.player.move(-self.camera_x, 0)
            screen.blit(image, image.get_rect(midbottom=rect.midbottom))
        if self.carried_baby is not None:
            rect = self.player.move(-self.camera_x, 0)
            screen.blit(self.baby_image, (rect.centerx - 12, rect.bottom - image.get_height() - 29))
        pg.draw.rect(screen, (16, 45, 72), (0, 0, WIDTH, 72))
        screen.blit(self.font.render(f'Score: {self.score}    Fish: {self.total - len(self.fish)} / {self.total}    Falls: {self.falls}    Hits: {self.hits}', True, 'white'), (18, 10))
        screen.blit(self.font.render('Arrows / A D: move    Space: jump    R: restart    Esc: quit', True, (195, 234, 255)), (18, 40))
        region = min(len(REGIONS) - 1, self.player.centerx // REGION_WIDTH)
        status = f'{REGIONS[region][0]} | 구조 {self.rescued}/3 | 저장 지점 {self.checkpoint_index + 1}'
        label = self.intro_font.render(status, True, 'white')
        pg.draw.rect(screen, (16, 45, 72), (12, 113, label.get_width()+16, 32), border_radius=5)
        screen.blit(label, (20, 116))
        legend = self.font.render('Orange: 10    Blue: 25    Gold: 50    Stomp crab: +30', True, 'white')
        pg.draw.rect(screen, (16, 45, 72), (10, HEIGHT - 35, legend.get_width() + 20, 30), border_radius=5)
        screen.blit(legend, (20, HEIGHT - 31))
        active = '    '.join(f'{ITEM_STYLE[kind][2]}: {seconds:.1f}s'
                             for kind, seconds in self.effects.items() if seconds > 0)
        if active:
            label = self.font.render(active, True, 'white')
            pg.draw.rect(screen, (16, 45, 72), (12, 77, label.get_width() + 16, 30), border_radius=5)
            screen.blit(label, (20, 80))
        if self.won:
            overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
            overlay.fill((8, 25, 45, 175))
            screen.blit(overlay, (0, 0))
            for text, font, y in [('Adventure complete!', self.big_font, 225),
                                  (f'Final score: {self.score} / {self.max_score}', self.font, 300),
                                  ('Press R to play again', self.font, 345)]:
                label = font.render(text, True, 'white')
                screen.blit(label, label.get_rect(center=(WIDTH // 2, y)))

    def draw_adventure(self, screen):
        region = min(len(REGIONS) - 1, self.player.centerx // REGION_WIDTH)
        for cave in self.caves:
            rect = cave['rect'].move(-self.camera_x, 0)
            screen.blit(self.cave_image, self.cave_image.get_rect(midbottom=rect.midbottom))
            if cave['found'] and not cave['treasure']:
                chest = pg.Rect(rect.right - 45, 515, 30, 30)
                screen.blit(self.chest_image, chest)
        for index, checkpoint in enumerate(self.checkpoints):
            rect = checkpoint.move(-self.camera_x, 0)
            screen.blit(self.igloo_image, self.igloo_image.get_rect(midbottom=rect.midbottom))
            if index == self.checkpoint_index:
                pg.draw.circle(screen, (111, 255, 151), (rect.centerx, rect.top-32), 5)
        for index, baby in enumerate(self.babies):
            if not baby['rescued'] and index != self.carried_baby:
                rect = baby['rect'].move(-self.camera_x, 0)
                screen.blit(self.baby_image, rect)
                label = self.font.render('!', True, (255, 232, 101))
                screen.blit(label, (rect.centerx - 4, rect.y - 25))
        if region == 3:
            for i in range(65):
                x = int((i * 137 - self.time * 180) % WIDTH)
                y = int((i * 83 + self.time * 45) % HEIGHT)
                pg.draw.line(screen, (238, 249, 255), (x, y), (x - 12, y + 4), 2)
        # An overview of the six regions and the camera position.
        for i, (_, color) in enumerate(REGIONS):
            pg.draw.rect(screen, color, (WIDTH - 210 + i * 32, HEIGHT - 30, 30, 12))
        marker = WIDTH - 210 + int(self.player.centerx / WORLD_WIDTH * 192)
        pg.draw.circle(screen, 'white', (marker, HEIGHT - 24), 4)

    def draw_intro(self, screen):
        screen.blit(self.background, (0, 0))
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((8, 25, 45, 210))
        screen.blit(overlay, (0, 0))
        title = self.intro_title_font.render('남극 펭귄의 물고기 모험', True, (223, 249, 255))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 55)))
        lines = [
            ('목표: 6개 구역의 물고기 30마리를 모으고 아기 펭귄 3마리 구조!', 'white'),
            ('이동: ← → 또는 A / D     점프: 스페이스바 / ↑ / W', 'white'),
            ('주황 물고기 10점 · 파랑 25점 · 황금 50점', (255, 223, 120)),
            ('초록 물약: 몸 크기 1.5배 · 적 돌파! 좁은 길도 통과 가능', ITEM_STYLE['grow'][0]),
            ('노랑 물약: 이동 속도 1.6배 (모든 물약 효과는 8초)', ITEM_STYLE['speed'][0]),
            ('보라 물약: 좌우 이동 반전! 발판은 아래에서 통과 가능', ITEM_STYLE['reverse'][0]),
            ('이글루에 닿으면 저장! 아기 펭귄을 데려오면 구조 +100점.', 'white'),
            ('게를 위에서 밟으면 처치하고 30점을 얻습니다.', (255, 155, 165)),
            ('미끄러운 얼음, 0.8초 뒤 무너지는 발판, 눈보라에 주의!', 'white'),
            ('피격·추락 시 이글루로 복귀. 점수 유지, 아이템 해제, 2초 무적.', 'white'),
            ('동굴 안 보물 +100점! 구조 중 추락하면 아기는 원래 자리로.', 'white'),
            ('R: 설명 화면부터 재시작     Esc: 게임 종료', (195, 234, 255)),
        ]
        for index, (text, color) in enumerate(lines):
            screen.blit(self.intro_font.render(text, True, color), (45, 105 + index * 32))
        pg.draw.rect(screen, (42, 104, 142), (125, 510, 550, 58), border_radius=12)
        prompt = self.intro_font.render('Enter 또는 스페이스바를 눌러 시작하세요', True, 'white')
        screen.blit(prompt, prompt.get_rect(center=(WIDTH // 2, 539)))


def main():
    pg.init()
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    pg.display.set_caption('Antarctic Penguin - Fish Adventure')
    game = Game()
    pg.display.set_icon(game.penguin_right)
    clock = pg.time.Clock()
    running = True
    try:
        while running:
            dt = min(clock.tick(60) / 1000, 1 / 30)
            jump = False
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        running = False
                    elif not game.started:
                        if event.key in (pg.K_RETURN, pg.K_SPACE):
                            game.started = True
                    elif event.key == pg.K_r:
                        game.reset()
                    elif event.key in (pg.K_SPACE, pg.K_UP, pg.K_w):
                        jump = True
            keys = pg.key.get_pressed()
            direction = int(keys[pg.K_RIGHT] or keys[pg.K_d]) - int(keys[pg.K_LEFT] or keys[pg.K_a])
            game.update(dt, direction, jump)
            game.draw(screen)
            pg.display.flip()
    finally:
        pg.quit()


if __name__ == '__main__':
    main()

