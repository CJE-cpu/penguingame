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
FISH_TYPES = {'orange': ('orange-fish-swim-1.png', (255, 255, 255), 10),
              'blue': ('orange-fish-swim-2.png', (100, 205, 255), 25),
              'gold': ('orange-fish-swim-3.png', (255, 230, 100), 50)}
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

    def draw(self, screen, camera_x):
        rect = self.rect.move(-camera_x, 0)
        color = (227, 81, 98)
        for dx in (-1, 1):
            cx = rect.centerx + dx * 15
            pg.draw.line(screen, color, (cx, rect.bottom - 8), (cx + dx * 10, rect.bottom - 1), 3)
            pg.draw.circle(screen, color, (cx + dx * 6, rect.y + 10), 7)
        pg.draw.ellipse(screen, color, rect.inflate(-6, -8).move(0, 4))
        for x in (rect.centerx - 8, rect.centerx + 8):
            pg.draw.circle(screen, 'white', (x, rect.y + 7), 5)
            pg.draw.circle(screen, (30, 35, 50), (x + (1 if self.speed > 0 else -1), rect.y + 7), 2)


class Game:
    def __init__(self):
        self.background = load_image('antarctica-background.png', (WIDTH, HEIGHT))
        self.penguin_left = load_image('penguin-left.png', (40, 52), keep_aspect=True)
        self.penguin_right = pg.transform.flip(self.penguin_left, True, False)
        self.big_penguin_left = load_image('penguin-left.png', (60, 78), keep_aspect=True)
        self.big_penguin_right = pg.transform.flip(self.big_penguin_left, True, False)
        self.fish_images = {}
        for kind, (filename, tint, points) in FISH_TYPES.items():
            image = load_image(filename, (36, 24), keep_aspect=True)
            if kind != 'orange':
                # Tint the body while retaining the original alpha and outlines.
                for x in range(image.get_width()):
                    for y in range(image.get_height()):
                        color = image.get_at((x, y))
                        if color.a and color.r > color.g * 1.15 and color.r > 80:
                            brightness = color.r / 255
                            image.set_at((x, y), (*[round(c * brightness) for c in tint], color.a))
            self.fish_images[kind] = image
        self.font = pg.font.Font(None, 30)
        self.big_font = pg.font.Font(None, 64)
        korean_font = pg.font.match_font('malgungothic, 맑은 고딕, nanumgothic')
        self.intro_font = pg.font.Font(korean_font, 21)
        self.intro_title_font = pg.font.Font(korean_font, 36)
        self.baby_image = load_image('penguin-left.png', (24, 31), keep_aspect=True)
        self.platforms = []
        self.platform_kinds = {}
        self.grounds = []
        for region in range(len(REGIONS)):
            offset = region * REGION_WIDTH
            gap = (65, 85, 70, 65, 100, 75)[region]
            layouts = [(0, 550, 330, 50), (330 + gap, 550, 400, 50),
                       (790 + gap, 550, REGION_WIDTH - 790 - gap, 50)]
            # Different ridge positions and heights distinguish each region.
            start = (175, 200, 155, 210, 175, 195)[region]
            level = (450, 455, 445, 450, 455, 445)[region]
            layouts += [(start, level, 180, 22), (start + 190, level - 90, 180, 22),
                        (start + 380, level - 180, 180, 22)]
            for index, (x, y, w, h) in enumerate(layouts):
                rect = pg.Rect(offset + x, y, w, h)
                self.platforms.append(rect)
                kind = 'ice' if region in (1, 3) else 'snow'
                if region == 4 and index in (3, 4, 5):
                    kind = 'crumble'
                self.platform_kinds[tuple(rect)] = kind
                if index < 3:
                    self.grounds.append(rect)
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
            for kind, x in [('orange', 245), ('orange', 1030)]:
                self.fish.append((kind, pg.Rect(offset + x, 515, 36, 24)))
            for index, kind in enumerate(('blue', 'blue', 'gold')):
                platform = self.platforms[region * 6 + 3 + index]
                self.fish.append((kind, pg.Rect(platform.centerx - 18, platform.top - 35, 36, 24)))
        self.total = len(self.fish)
        self.score = 0
        self.max_score = sum(FISH_TYPES[kind][2] for kind, rect in self.fish)
        self.enemies = [Enemy(self.platforms[region * 6 + 1], 65 + region * 8)
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
        self.items = [(kind, pg.Rect(offset + x, y, 30, 30))
                      for offset in range(0, WORLD_WIDTH, REGION_WIDTH)
                      for kind, x, y in [('grow', 140, 510), ('speed', 465, 510),
                                         ('reverse', 710, 510)]]
        self.checkpoints = [pg.Rect(i * REGION_WIDTH + 30, 490, 95, 60)
                            for i in range(len(REGIONS))]
        self.checkpoint_index = 0
        self.spawn = (55, 498)
        self.crumbles = {}  # key -> (elapsed since stepped on, time left hidden)
        self.caves = [{'rect': pg.Rect(i * REGION_WIDTH + 880, 420, 180, 130),
                       'found': False, 'treasure': False} for i in (2, 4)]
        self.babies = []
        for region in (1, 3, 5):
            platform = self.platforms[region * 6 + 5]
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

    def resize_player(self, size):
        candidate = pg.Rect((0, 0), size)
        candidate.midbottom = self.player.midbottom
        candidate.x = max(0, min(WORLD_WIDTH - candidate.width, candidate.x))
        # Leave a growth pickup available if a wall or ceiling blocks expansion.
        if any(candidate.colliderect(platform) for platform in self.active_platforms()):
            return False
        self.player = candidate
        self.x, self.y = map(float, candidate.topleft)
        return True

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
        if not self.effects['grow'] and self.player.size != (40, 52):
            self.resize_player((40, 52))
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
        for platform in self.active_platforms():
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
        for platform in self.active_platforms():
            touching_top = (self.velocity_y >= 0 and self.player.bottom == platform.top
                            and self.player.right > platform.left and self.player.left < platform.right)
            if self.player.colliderect(platform) or touching_top:
                if self.velocity_y > 0:
                    self.player.bottom = platform.top
                    self.on_ground = True
                    self.surface_kind = self.platform_kinds[tuple(platform)]
                    if self.surface_kind == 'crumble':
                        self.crumbles.setdefault(tuple(platform), (0.0, 0.0))
                elif self.velocity_y < 0:
                    self.player.top = platform.bottom
                self.y = float(self.player.y)
                self.velocity_y = 0.0
        # Descending from above is a stomp; side and upward contact cause damage.
        for enemy in list(self.enemies):
            if not self.player.colliderect(enemy.rect):
                continue
            if self.velocity_y > 0 and previous_bottom <= enemy.rect.top + 3:
                self.enemies.remove(enemy)
                self.score += ENEMY_POINTS
                self.defeated += 1
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
            elif kind == 'grow' and not self.resize_player((60, 78)):
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
        background_x = -int(self.camera_x * 0.2) % WIDTH
        screen.blit(self.background, (background_x - WIDTH, 0))
        screen.blit(self.background, (background_x, 0))
        # Show water in the ground gaps so falls are visually clear.
        pg.draw.rect(screen, (24, 88, 130), (0, 550, WIDTH, 50))
        self.draw_adventure(screen)
        for platform in self.active_platforms():
            rect = platform.move(-self.camera_x, 0)
            kind = self.platform_kinds[tuple(platform)]
            color = (92, 208, 238) if kind == 'ice' else (180, 144, 158) if kind == 'crumble' else (96, 185, 221)
            pg.draw.rect(screen, color, rect, border_radius=5)
            pg.draw.rect(screen, (223, 249, 255), (rect.x, rect.y, rect.width, 7), border_radius=3)
            if kind == 'crumble':
                for x in range(rect.x + 15, rect.right, 35):
                    pg.draw.lines(screen, (83, 75, 109), False, [(x, rect.y + 7), (x + 8, rect.y + 13), (x + 3, rect.bottom)], 2)
        for index, (kind, fish) in enumerate(self.fish):
            bob = round(math.sin(self.time * 4 + index) * 3)
            screen.blit(self.fish_images[kind], fish.move(-self.camera_x, bob))
        for enemy in self.enemies:
            enemy.draw(screen, self.camera_x)
        for kind, rect in self.items:
            rect = rect.move(-self.camera_x, 0)
            color, symbol, _ = ITEM_STYLE[kind]
            pg.draw.rect(screen, color, rect, border_radius=7)
            pg.draw.rect(screen, (245, 250, 255), rect, width=2, border_radius=7)
            label = self.font.render(symbol, True, (16, 45, 72))
            screen.blit(label, label.get_rect(center=rect.center))
        if self.player.size == (60, 78):
            image = self.big_penguin_right if self.facing_right else self.big_penguin_left
        else:
            image = self.penguin_right if self.facing_right else self.penguin_left
        if not self.invincible or int(self.time * 10) % 2 == 0:
            screen.blit(image, self.player.move(-self.camera_x, 0))
        if self.carried_baby is not None:
            rect = self.player.move(-self.camera_x, 0)
            screen.blit(self.baby_image, (rect.centerx - 12, rect.top - 29))
        pg.draw.rect(screen, (16, 45, 72), (0, 0, WIDTH, 72))
        screen.blit(self.font.render(f'Score: {self.score}    Fish: {self.total - len(self.fish)} / {self.total}    Falls: {self.falls}    Hits: {self.hits}', True, 'white'), (18, 10))
        screen.blit(self.font.render('Arrows / A D: move    Space: jump    R: restart    Esc: quit', True, (195, 234, 255)), (18, 40))
        region = min(len(REGIONS) - 1, self.player.centerx // REGION_WIDTH)
        status = f'{REGIONS[region][0]} | 구조 {self.rescued}/3 | 저장 지점 {self.checkpoint_index + 1}'
        screen.blit(self.intro_font.render(status, True, (20, 45, 70)), (18, 116))
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
        tint = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        tint.fill((*REGIONS[region][1], 45 if region != 2 else 95))
        screen.blit(tint, (0, 0))
        for cave in self.caves:
            rect = cave['rect'].move(-self.camera_x, 0)
            pg.draw.ellipse(screen, (170, 206, 232), rect.inflate(24, 24))
            pg.draw.ellipse(screen, (22, 35, 67), rect)
            for dx in (18, 45, 100, 135):
                pg.draw.polygon(screen, (131, 216, 249), [(rect.x + dx, rect.y + 15),
                                (rect.x + dx + 12, rect.y + 15), (rect.x + dx + 6, rect.y + 48)])
            if cave['found'] and not cave['treasure']:
                chest = pg.Rect(rect.right - 45, 515, 30, 30)
                pg.draw.rect(screen, (240, 186, 66), chest, border_radius=4)
                pg.draw.rect(screen, (255, 242, 156), chest, 3, border_radius=4)
                pg.draw.line(screen, (120, 78, 42), chest.midtop, chest.midbottom, 3)
        for index, checkpoint in enumerate(self.checkpoints):
            rect = checkpoint.move(-self.camera_x, 0)
            pg.draw.ellipse(screen, (225, 245, 255), rect)
            pg.draw.rect(screen, (225, 245, 255), (rect.x, 520, rect.width, 30))
            pg.draw.ellipse(screen, (35, 66, 98), (rect.centerx - 15, 517, 30, 42))
            pg.draw.line(screen, (40, 65, 95), (rect.right, 455), (rect.right, 540), 3)
            flag = (112, 242, 150) if index == self.checkpoint_index else (255, 215, 106)
            pg.draw.polygon(screen, flag, [(rect.right, 455), (rect.right + 32, 466), (rect.right, 480)])
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
            ('초록 + : 몸 크기 1.5배', ITEM_STYLE['grow'][0]),
            ('노랑 >> : 이동 속도 1.6배', ITEM_STYLE['speed'][0]),
            ('보라 <> : 좌우 이동 반전! (A / D도 반전됩니다)', ITEM_STYLE['reverse'][0]),
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

