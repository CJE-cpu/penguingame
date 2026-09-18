"""Antarctic penguin platformer. Arrows/A/D: move; Space: jump; R: restart."""
from pathlib import Path
import math
import pygame as pg
from ui import IceUI
from animation import PenguinAnimation
from enemies import Enemy, ENEMY_INFO
from feedback import InteractionEffects

WIDTH, HEIGHT = 800, 600
REGION_WIDTH = 1200
REGIONS = [('눈 덮인 해안', (109, 192, 226)), ('미끄러운 빙하', (80, 211, 239)),
           ('얼음 동굴', (106, 129, 179)), ('눈보라 고원', (159, 183, 202)),
           ('갈라진 빙붕', (148, 183, 230)), ('펭귄의 보금자리', (132, 206, 183))]
WORLD_WIDTH = REGION_WIDTH * len(REGIONS)
BLEND_DISTANCE = 180
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
ITEM_STYLE = {'grow': ((126, 224, 126), '+', 'BIG'),
              'speed': ((255, 212, 92), '>>', 'FAST'),
              'reverse': ((221, 142, 255), '<>', 'REVERSE')}
REGION_HINTS = ['해안 · 게 순찰, 물범 돌진', '빙하 · 긴 관성, 튀는 정령',
                '동굴 · 어둠과 탐험 조명', '눈보라 · 돌풍과 도둑갈매기',
                '빙붕 · 무너지는 다리 주의', '보금자리 · 이글루 주변은 안전지대']


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


class Game:
    def __init__(self):
        self.background = load_image('antarctica-background.png', (WIDTH, HEIGHT))
        self.scene_backgrounds = [load_image('scene-' + scene + '.png', (WIDTH, HEIGHT)) for scene in SCENES]
        self.penguin_left = load_image('penguin-adult-left.png', (40, 52), keep_aspect=True)
        self.penguin_right = pg.transform.flip(self.penguin_left, True, False)
        self.big_penguin_left = load_image('penguin-adult-left.png', (60, 78), keep_aspect=True)
        self.big_penguin_right = pg.transform.flip(self.big_penguin_left, True, False)
        self.animation = PenguinAnimation(DATA)
        self.feedback = InteractionEffects()
        self.fish_images = {}
        for kind, (filename, tint, points) in FISH_TYPES.items():
            image = load_image(filename, (36, 24), keep_aspect=True)
            self.fish_images[kind] = image
        self.ui = IceUI()
        self.font = self.ui.body
        self.big_font = self.ui.title
        self.intro_font = self.ui.body
        self.intro_title_font = self.ui.title
        self.baby_image = load_image('penguin-baby-left.png', (24, 31), keep_aspect=True)
        self.crab_image = load_image('crab-enemy.png', (44, 30), keep_aspect=True)
        self.enemy_images = {'crab':[self.crab_image]}
        for kind, filenames in [('seal', ['seal-patrol','seal-charge']),
                                ('skua',['skua-wings-up','skua-wings-down']),
                                ('spirit',['ice-spirit-standing','ice-spirit-jumping'])]:
            self.enemy_images[kind] = [load_image(name+'.png', ENEMY_INFO[kind][1], keep_aspect=True) for name in filenames]
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
        self.animation.reset()
        self.feedback.reset()
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
        self.enemies = []
        for region, kinds in enumerate([('crab','seal'), ('seal','spirit'), ('spirit','spirit'),
                                       ('skua','skua'), ('spirit','seal'), ('crab','skua')]):
            for index, kind in enumerate(kinds):
                platform = (self.region_ledges[region][1] if index and kind == 'spirit'
                            else self.region_grounds[region][0 if index else -1])
                if index and kind == 'seal':
                    platform = self.region_grounds[region][min(1,len(self.region_grounds[region])-1)]
                enemy = Enemy(platform, 55+region*7, kind)
                # Keep ground enemies out of the checkpoint's immediate vicinity.
                if platform == self.region_grounds[region][0]:
                    enemy.left = platform.left+150
                    enemy.x = float(enemy.left)
                    enemy.rect.x = enemy.left
                self.enemies.append(enemy)
        self.max_score += sum(enemy.points for enemy in self.enemies)
        self.defeated = 0
        self.hits = 0
        self.invincible = 0.0
        self.camera_x = 0
        self.display_region = 0
        self.region_banner = 0.0
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
                if kind == 'reverse' and region not in (2,4):
                    continue
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
        self.in_sanctuary = False
        self.max_score += len(self.babies) * 100 + len(self.caves) * 100

    def active_platforms(self):
        return [p for p in self.platforms if self.crumbles.get(tuple(p), (0, 0))[1] <= 0]

    def scene_weights(self):
        """Blend across either side of a boundary, including when returning."""
        x = self.player.centerx
        for right in range(1, len(REGIONS)):
            boundary = right * REGION_WIDTH
            if abs(x - boundary) <= BLEND_DISTANCE:
                t = (x - boundary + BLEND_DISTANCE) / (2 * BLEND_DISTANCE)
                t = t * t * (3 - 2 * t)
                return [(right - 1, 1 - t), (right, t)]
        return [(max(0, min(len(REGIONS)-1, x // REGION_WIDTH)), 1.0)]

    def update_presentation(self, dt):
        target = max(0, min(WORLD_WIDTH-WIDTH, self.player.centerx-WIDTH//2))
        self.camera_x += (target-self.camera_x) * (1-math.exp(-10*dt))
        region = max(0, min(len(REGIONS)-1, self.player.centerx//REGION_WIDTH))
        self.region_banner = max(0, self.region_banner-dt)
        if region != self.display_region:
            self.display_region = region
            self.region_banner = 2.4

    def update_adventure(self, dt):
        sanctuary = self.player.colliderect(self.checkpoints[-1].inflate(90,60))
        if sanctuary:
            self.invincible = max(self.invincible,0.15)
            if not self.in_sanctuary:
                self.feedback.emit(self.player.midtop,'보금자리의 안전지대',(160,239,193))
        self.in_sanctuary = sanctuary
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
                if index != self.checkpoint_index:
                    self.feedback.emit(checkpoint.midtop, '저장 완료', (169,235,255))
                self.checkpoint_index = index
                self.spawn = (checkpoint.x + 25, 498)
                if self.carried_baby is not None:
                    self.babies[self.carried_baby]['rescued'] = True
                    self.carried_baby = None
                    self.rescued += 1
                    self.score += 100
                    self.feedback.emit(checkpoint.midtop, '친구 구조! +100', (157,238,183))
        for index, baby in enumerate(self.babies):
            if (not baby['rescued'] and self.carried_baby is None
                    and self.player.colliderect(baby['rect'])):
                self.carried_baby = index
                self.feedback.emit(baby['rect'].midtop, '이글루로 데려가요!', (178,227,255))
        for cave in self.caves:
            if self.player.colliderect(cave['rect']):
                cave['found'] = True
                chest = pg.Rect(cave['rect'].right - 45, 515, 30, 30)
                if not cave['treasure'] and self.player.colliderect(chest):
                    cave['treasure'] = True
                    self.score += 100
                    self.feedback.emit(chest.midtop, '보물 발견! +100', (255,228,142))

    def respawn(self, hit=False):
        self.animation.reset()
        self.feedback.reset()
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
        self.feedback.emit(self.player.midtop, '피격! 저장 지점 복귀' if hit else '저장 지점에서 다시!', (205,235,255))
        self.camera_x = max(0, min(WORLD_WIDTH - WIDTH, self.player.centerx - WIDTH // 2))
        self.display_region = self.player.centerx // REGION_WIDTH
        self.region_banner = 0.0

    def update(self, dt, direction=0, jump=False):
        if not self.started:
            return
        self.time += dt
        if self.won:
            return
        self.invincible = max(0.0, self.invincible - dt)
        self.feedback.update(dt)
        was_grounded = self.on_ground
        previous_x = self.player.x
        self.update_adventure(dt)
        previous_bottom = self.player.bottom
        for enemy in self.enemies:
            enemy.update(dt, self.player)
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
        wind = -(65+30*math.sin(self.time*1.2)) * dict(self.scene_weights()).get(3, 0)
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
            if self.effects['grow'] or (self.velocity_y > 0 and previous_bottom <= enemy.previous_top + 3):
                self.enemies.remove(enemy)
                self.score += enemy.points
                self.feedback.emit(enemy.rect.midtop, f'{ENEMY_INFO[enemy.kind][0]} 처치 +{enemy.points}', (255,219,132))
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
                self.feedback.emit(rect.center, f'+{FISH_TYPES[kind][2]}', (255,232,151))
            else:
                remaining_fish.append((kind, rect))
        self.fish = remaining_fish
        remaining_items = []
        for kind, rect in self.items:
            if not self.player.colliderect(rect):
                remaining_items.append((kind, rect))
            else:
                # Idempotent: a second reversal refreshes its timer, never flips twice.
                repeated = self.effects[kind] > 0
                self.effects[kind] = ITEM_DURATION
                name = {'grow':'성장! 적 돌파', 'speed':'가속! 속도 증가', 'reverse':'주의! 좌우 반전'}[kind]
                if repeated:
                    name = {'grow':'성장', 'speed':'가속', 'reverse':'반전'}[kind]+' 시간 갱신'
                self.feedback.emit(rect.center, name, ITEM_STYLE[kind][0])
        self.items = remaining_items
        self.update_adventure(0)
        if not self.fish and self.rescued == len(self.babies):
            self.won = True
        if self.player.top > HEIGHT:
            self.respawn()
            return
        self.animation.update(dt, self.player, self.velocity_y, self.on_ground,
                              was_grounded, abs(self.player.x-previous_x))
        self.update_presentation(dt)

    def draw(self, screen):
        if not self.started:
            self.draw_intro(screen)
            return
        background_x = -int(self.camera_x * 0.2) % WIDTH
        for index, (region, weight) in enumerate(self.scene_weights()):
            background = self.scene_backgrounds[region]
            if index:
                background = background.copy()
                background.set_alpha(round(255*weight))
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
            enemy.draw(screen, self.camera_x, self.enemy_images)
        for kind, rect in self.items:
            rect = rect.move(-self.camera_x, 0)
            bob = round(math.sin(self.time*3+rect.x*0.01)*3)
            color = ITEM_STYLE[kind][0]
            pg.draw.ellipse(screen, color, (rect.x+2,rect.bottom-3,26,5),2)
            screen.blit(self.item_images[kind], rect.move(0,bob))
        image = self.animation.image(self.effects['grow'], self.facing_right)
        self.feedback.draw_aura(self, screen)
        self.animation.draw_puffs(screen, self.camera_x)
        if not self.invincible or int(self.time * 10) % 2 == 0:
            rect = self.player.move(-self.camera_x, 0)
            screen.blit(image, image.get_rect(midbottom=rect.midbottom))
        if self.carried_baby is not None:
            rect = self.player.move(-self.camera_x, 0)
            screen.blit(self.baby_image, (rect.centerx - 12, rect.bottom - image.get_height() - 29))
        self.draw_region_atmosphere(screen)
        self.feedback.draw(self, screen)
        self.ui.hud(self, screen, REGIONS)
        self.ui.transition(self, screen, REGIONS)
        if self.region_banner > 0:
            label = self.ui.small.render(REGION_HINTS[self.display_region],True,(28,64,87))
            self.ui.panel(screen,(490,149,298,31))
            screen.blit(label,(499,154))
        if self.won:
            self.ui.finish(self, screen)

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
            if index == len(self.checkpoints)-1:
                pg.draw.ellipse(screen,(151,222,190),rect.inflate(70,12),2)
            screen.blit(self.igloo_image, self.igloo_image.get_rect(midbottom=rect.midbottom))
            if index == self.checkpoint_index:
                pg.draw.circle(screen, (111, 255, 151), (rect.centerx, rect.top-32), 5)
        for index, baby in enumerate(self.babies):
            if not baby['rescued'] and index != self.carried_baby:
                rect = baby['rect'].move(-self.camera_x, 0)
                screen.blit(self.baby_image, rect)
                label = self.font.render('!', True, (255, 232, 101))
                screen.blit(label, (rect.centerx - 4, rect.y - 25))
        snow_weight = dict(self.scene_weights()).get(3, 0)
        if snow_weight > 0:
            snow = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
            for i in range(65):
                x = int((i * 137 - self.time * 180) % WIDTH)
                y = int((i * 83 + self.time * 45) % HEIGHT)
                pg.draw.line(snow, (238, 249, 255, round(255*snow_weight)), (x, y), (x - 12, y + 4), 2)
            screen.blit(snow, (0, 0))

    def draw_region_atmosphere(self, screen):
        weights = dict(self.scene_weights())
        cave = weights.get(2,0)
        if cave:
            shade = pg.Surface((WIDTH,HEIGHT),pg.SRCALPHA)
            shade.fill((4,14,35,round(105*cave)))
            center = (round(self.player.centerx-self.camera_x),self.player.centery)
            for radius,alpha in [(220,70),(170,42),(115,15)]:
                pg.draw.ellipse(shade,(4,14,35,round(alpha*cave)),
                                (center[0]-radius,center[1]-radius,radius*2,radius*2))
            screen.blit(shade,(0,0))
        if weights.get(0,0):
            for i in range(12):
                x = round((i*79+self.time*20)%WIDTH)
                y = 557+round(math.sin(self.time*2+i)*3)
                pg.draw.line(screen,(166,227,245),(x,y),(x+22,y),2)
    def draw_intro(self, screen):
        self.ui.intro(self, screen)


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
                            game.region_banner = 2.4
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

