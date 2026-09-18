"""Antarctic penguin platformer. Arrows/A/D: move; Space: jump; R: restart."""
from pathlib import Path
import math
import pygame as pg

WIDTH, HEIGHT = 800, 600
WORLD_WIDTH = 2400
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
        # Three regions, with small ground gaps and optional ascending routes.
        self.platforms = []
        for offset in (0, 800, 1600):
            self.platforms.extend([pg.Rect(offset, 550, 300, 50),
                                   pg.Rect(offset + 390, 550, 410, 50),
                                   pg.Rect(offset + 180, 450, 180, 22),
                                   pg.Rect(offset + 370, 360, 180, 22),
                                   pg.Rect(offset + 560, 270, 180, 22)])
        self.reset()

    def reset(self):
        self.player = pg.Rect(55, 498, 40, 52)
        self.x, self.y = float(self.player.x), float(self.player.y)
        self.velocity_y = 0.0
        self.on_ground = True
        self.facing_right = True
        self.fish = []
        for offset in (0, 800, 1600):
            for kind, x, y in [('orange', 65, 515), ('orange', 470, 515),
                               ('blue', 250, 415), ('blue', 445, 325),
                               ('gold', 640, 235), ('orange', 745, 515)]:
                self.fish.append((kind, pg.Rect(offset + x, y, 36, 24)))
        self.total = len(self.fish)
        self.score = 0
        self.max_score = sum(FISH_TYPES[kind][2] for kind, rect in self.fish)
        self.enemies = [Enemy(self.platforms[region * 5 + index], 65 + region * 15)
                        for region in range(3) for index in (1, 3)]
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
                      for offset in (0, 800, 1600)
                      for kind, x, y in [('grow', 140, 510), ('speed', 305, 415),
                                         ('reverse', 590, 510)]]

    def resize_player(self, size):
        candidate = pg.Rect((0, 0), size)
        candidate.midbottom = self.player.midbottom
        candidate.x = max(0, min(WORLD_WIDTH - candidate.width, candidate.x))
        # Leave a growth pickup available if a wall or ceiling blocks expansion.
        if any(candidate.colliderect(platform) for platform in self.platforms):
            return False
        self.player = candidate
        self.x, self.y = map(float, candidate.topleft)
        return True

    def respawn(self, hit=False):
        self.effects = {kind: 0.0 for kind in ITEM_STYLE}
        self.player.size = (40, 52)
        self.player.topleft = (55, 498)
        self.x, self.y = map(float, self.player.topleft)
        self.velocity_y = 0.0
        self.on_ground = True
        if hit:
            self.hits += 1
        else:
            self.falls += 1
        self.invincible = 2.0
        self.camera_x = 0

    def update(self, dt, direction=0, jump=False):
        if not self.started:
            return
        self.time += dt
        if self.won:
            return
        self.invincible = max(0.0, self.invincible - dt)
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
        self.x += direction * speed * dt
        self.player.x = round(self.x)
        for platform in self.platforms:
            if self.player.colliderect(platform):
                if direction > 0:
                    self.player.right = platform.left
                elif direction < 0:
                    self.player.left = platform.right
                self.x = float(self.player.x)
        self.player.x = max(0, min(WORLD_WIDTH - self.player.width, self.player.x))
        if self.player.x != round(self.x):
            self.x = float(self.player.x)
        self.velocity_y += GRAVITY * dt
        self.y += self.velocity_y * dt
        self.player.y = round(self.y)
        self.on_ground = False
        for platform in self.platforms:
            touching_top = (self.velocity_y >= 0 and self.player.bottom == platform.top
                            and self.player.right > platform.left and self.player.left < platform.right)
            if self.player.colliderect(platform) or touching_top:
                if self.velocity_y > 0:
                    self.player.bottom = platform.top
                    self.on_ground = True
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
        if not self.fish:
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
        for platform in self.platforms:
            rect = platform.move(-self.camera_x, 0)
            pg.draw.rect(screen, (96, 185, 221), rect, border_radius=5)
            pg.draw.rect(screen, (223, 249, 255), (rect.x, rect.y, rect.width, 7), border_radius=3)
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
        pg.draw.rect(screen, (16, 45, 72), (0, 0, WIDTH, 72))
        screen.blit(self.font.render(f'Score: {self.score}    Fish: {self.total - len(self.fish)} / {self.total}    Falls: {self.falls}    Hits: {self.hits}', True, 'white'), (18, 10))
        screen.blit(self.font.render('Arrows / A D: move    Space: jump    R: restart    Esc: quit', True, (195, 234, 255)), (18, 40))
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
            for text, font, y in [('All fish collected!', self.big_font, 225),
                                  (f'Final score: {self.score} / {self.max_score}', self.font, 300),
                                  ('Press R to play again', self.font, 345)]:
                label = font.render(text, True, 'white')
                screen.blit(label, label.get_rect(center=(WIDTH // 2, y)))

    def draw_intro(self, screen):
        screen.blit(self.background, (0, 0))
        overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        overlay.fill((8, 25, 45, 210))
        screen.blit(overlay, (0, 0))
        title = self.intro_title_font.render('남극 펭귄의 물고기 모험', True, (223, 249, 255))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 55)))
        lines = [
            ('목표: 넓은 남극 맵에서 물고기 18마리를 모두 모으세요!', 'white'),
            ('이동: ← → 또는 A / D     점프: 스페이스바 / ↑ / W', 'white'),
            ('주황 물고기 10점 · 파랑 25점 · 황금 50점', (255, 223, 120)),
            ('초록 + : 몸 크기 1.5배', ITEM_STYLE['grow'][0]),
            ('노랑 >> : 이동 속도 1.6배', ITEM_STYLE['speed'][0]),
            ('보라 <> : 좌우 이동 반전! (A / D도 반전됩니다)', ITEM_STYLE['reverse'][0]),
            ('아이템 효과는 8초간 유지되며 함께 적용될 수 있어요.', 'white'),
            ('게를 위에서 밟으면 처치하고 30점을 얻습니다.', (255, 155, 165)),
            ('옆에서 닿거나 물에 빠지면 시작 위치로 돌아갑니다.', 'white'),
            ('점수는 유지되고 아이템 효과는 해제됩니다. 복귀 후 2초 무적!', 'white'),
            ('적 처치는 선택! 물고기를 모두 모으면 성공입니다.', 'white'),
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

