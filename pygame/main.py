"""Antarctic penguin platformer. Arrows/A/D: move; Space: jump; R: restart."""
from pathlib import Path
from datetime import datetime
from uuid import uuid4
import asyncio
import json
import math
import sys
import pygame as pg
from ui import IceUI
from animation import PenguinAnimation
from enemies import Enemy, ENEMY_INFO
from feedback import InteractionEffects
from motion import CombatMotion, BabyCompanion
from adventure import AdventureContent
from tutorial import Coach, TutorialStage
from art import WorldArt, contact_shadow, atlas_cells, fit_cycle
from window import GameWindow
from cave import CaveExpedition
from records import ScoreRecords, ScoreUI
from progress import AdventureSave
from ending import EndingSequence, ENDING_NAMES
from sound import GameAudio
from boss import SealBoss, SkuaBoss

WIDTH, HEIGHT = 800, 600
NORMAL_PLAYER_SIZE = (40, 52)
# Keep every biome spacious enough for exploration and combat beats to breathe.
# MAP_LAYOUTS use a 1,200 px authoring grid, so changing this value expands all
# terrain and terrain-anchored objects together without introducing seams.
REGION_WIDTH = 2100
MAP_SCALE = REGION_WIDTH / 1200
REGIONS = [('눈 덮인 해안', (109, 192, 226)), ('미끄러운 빙하', (80, 211, 239)),
           ('얼음 동굴', (106, 129, 179)), ('눈보라 고원', (159, 183, 202)),
           ('갈라진 빙붕', (148, 183, 230)), ('펭귄의 보금자리', (132, 206, 183))]
WORLD_WIDTH = REGION_WIDTH * len(REGIONS)
BLEND_DISTANCE = 300
SCENES = ['snow-coast', 'glacier-canyon', 'ice-cave', 'blizzard-plateau', 'fractured-shelf', 'sunset-home']
SCENE_GRADES = (
    ((201, 236, 246), 10), ((178, 224, 242), 13),
    ((31, 72, 105), 18), ((205, 221, 239), 12),
    ((184, 209, 239), 13), ((255, 205, 180), 15),
)
# Each region has a different silhouette and optional upper routes.
MAP_LAYOUTS = [
    ([(0,550,360), (430,550,370), (870,550,330)],
     [(70,390,80), (180,450,190), (370,360,170), (550,270,160),
      (735,360,150), (900,450,160), (1080,365,90)]),
    ([(0,550,280), (360,530,220), (660,550,210), (950,550,250)],
     [(75,365,85), (160,450,140), (330,360,150), (510,280,190),
      (730,370,140), (910,455,150), (1080,360,80)]),
    ([(0,550,1200)],
     [(140,450,150), (290,355,160), (400,265,150), (300,175,170),
      (980,360,160), (1050,450,130)]),
    ([(0,550,310), (370,520,250), (690,490,230), (995,550,205)],
     [(60,370,80), (160,450,180), (350,365,200), (575,280,180),
      (780,205,190), (1040,390,90)]),
    ([(0,550,250), (315,550,230), (610,550,590)],
     [(65,390,100), (180,460,140), (345,390,150),
      (1025,460,75), (1110,390,65)]),
    ([(0,550,350), (420,550,780)],
     [(70,375,90), (190,450,200), (395,365,160), (575,280,180),
      (785,365,160), (975,450,180), (1100,360,70)])]
FISH_TYPES = {'orange': 10, 'blue': 25, 'gold': 50}
DATA = Path(__file__).resolve().parent / 'data'
GRAVITY = 1800
MOVE_SPEED = 270
JUMP_SPEED = -650
JUMP_HOLD_TIME = 0.22
JUMP_HOLD_FORCE = 1050
JUMP_RELEASE_SPEED = -390
COYOTE_TIME = 0.1
JUMP_BUFFER_TIME = 0.12
ITEM_DURATION = 8.0
GROW_EXIT_INVINCIBILITY = 1.5
RESPAWN_INVINCIBILITY = 3.0
RESPAWN_CLEAR_RADIUS = 280
STARTING_LIVES = 3
TIME_BONUS_MAX = 1800
TIME_BONUS_RATE = 2
ITEM_STYLE = {'grow': ((126, 224, 126), '+', 'BIG'),
              'speed': ((255, 212, 92), '>>', 'FAST'),
              'shield': ((123, 211, 255), 'O', 'SHIELD')}
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
    def __init__(self, score_path=None, progress_path=None):
        self.region_width = REGION_WIDTH
        self.world_width = WORLD_WIDTH
        # One oversized panorama per region; never join non-seamless image edges.
        # Scene panoramas contain no transparency. Converting them to the
        # display format avoids a per-pixel alpha blend across 720,000 pixels
        # on every outdoor frame and twice that amount at region boundaries.
        self.scene_backgrounds = [
            load_image('scene-' + scene + '.png', (WIDTH + 400, HEIGHT)).convert()
            for scene in SCENES
        ]
        self.animation = PenguinAnimation(DATA)
        self.penguin_left = self.animation.cycles['idle'][0]
        self.penguin_right = pg.transform.flip(self.penguin_left,True,False)
        self.big_penguin_left = pg.transform.scale(self.penguin_left,(96,84))
        self.big_penguin_right = pg.transform.flip(self.big_penguin_left,True,False)
        self.art = WorldArt(DATA)
        self.ocean_background = load_image('ocean-panorama-v2.png',(1800,HEIGHT)).convert()
        self.feedback = InteractionEffects()
        self.combat = CombatMotion()
        self.companion = BabyCompanion()
        self.fish_images = {kind:self.art.fish(kind,0) for kind in FISH_TYPES}
        self.ui = IceUI()
        self.audio = GameAudio(DATA)
        self.region_hint_labels = [self.ui.small.render(text, True, (28, 64, 87))
                                   for text in REGION_HINTS]
        self.ending_badge_label = self.ui.small.render('E  엔딩', True, (255, 255, 255))
        self.font = self.ui.body
        self.big_font = self.ui.title
        self.intro_font = self.ui.body
        self.intro_title_font = self.ui.title
        self.baby_image = self.art.baby('idle',0)
        self.life_item_image = self.make_life_item_image()
        self.enemy_images = self.art.enemies
        self.boss_images = {
            name: load_image(f'seal-boss-{name}.png', (180, 110))
            for name in ('idle', 'roar', 'warning', 'charge', 'stunned', 'defeated')
        }
        skua_cells = fit_cycle(atlas_cells(DATA/'skua-boss-atlas.png', 4, 2),
                               (180, 115), padding=3, anchor='center')
        self.skua_boss_images = dict(zip(
            ('hover-up', 'hover-down', 'warning', 'dive', 'carry',
             'stunned', 'hit', 'defeated'), skua_cells))
        self.crab_image = self.enemy_images['crab'][0]
        self.igloo_image = load_image('igloo-checkpoint.png', (112, 85), keep_aspect=True)
        self.cave_image = load_image('ice-cave-entrance.png', (180, 135), keep_aspect=True)
        self.chest_image = load_image('golden-treasure-chest.png', (36, 30), keep_aspect=True)
        self.item_images = {kind: load_image(filename + '-potion.png', (30, 36), keep_aspect=True)
                            for kind, filename in [('grow', 'growth'), ('speed', 'speed'),
                                                   ('shield', 'shield')]}
        # A restrained three-tone palette keeps platforms readable against the
        # painted scenery without filling every ledge with crystals and rocks.
        self.platform_palettes = {
            'snow': ((239, 249, 252), (158, 207, 226), (91, 151, 181)),
            'ice': ((225, 250, 253), (120, 204, 225), (62, 145, 181)),
            'cave': ((205, 229, 239), (105, 155, 184), (55, 102, 137)),
            'fracture': ((226, 232, 250), (145, 157, 207), (83, 89, 151)),
            'crumble': ((236, 225, 247), (163, 146, 204), (101, 82, 157)),
            'sunset': ((255, 241, 240), (222, 177, 196), (151, 113, 157)),
        }
        self.platform_textures = {}
        self.platform_images = {
            kind: self.platform_texture(kind, (160, 30), variant='thin')
            for kind in self.platform_palettes
        }
        # Kept as a public preview collection for layout checks and UI cards.
        self.shelf_images = self.platform_images
        # Reuse transparent effect buffers instead of allocating two full
        # screen surfaces every rendered frame in the browser build.
        self.weather_layer = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        self.marker_layer = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        self.atmosphere_layer = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        self.collectible_layer = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        self.quality_levels = ('performance', 'balanced', 'high')
        # WebAssembly alpha drawing is much slower than native rendering.
        # Performance mode keeps native resolution and sprites intact; it only
        # reduces decorative particles, light rays and procedural texture work.
        # Balanced avoids expensive full-detail effects and window resampling
        # on the first run; high quality remains available from the options key.
        self.quality_index = 0 if sys.platform == 'emscripten' else 1
        self.adaptive_quality_index = 2
        self.render_ms_average = 0.0
        self.fast_render_frames = 0
        self.platforms = []
        self.platform_kinds = {}
        self.platform_variants = {}
        self.grounds = []
        self.region_grounds = []
        self.region_ledges = []
        for region, (ground_layout, ledge_layout) in enumerate(MAP_LAYOUTS):
            offset = region * REGION_WIDTH
            grounds = [pg.Rect(offset+round(x*MAP_SCALE), y, round(w*MAP_SCALE), HEIGHT-y) for x,y,w in ground_layout]
            ledges = [pg.Rect(offset+round(x*MAP_SCALE), y, round(w*MAP_SCALE), 24) for x,y,w in ledge_layout]
            self.region_grounds.append(grounds)
            self.region_ledges.append(ledges)
            self.grounds.extend(grounds)
            for platform_index, rect in enumerate(grounds + ledges):
                self.platforms.append(rect)
                kind = ('ice' if region in (1, 3) else 'cave' if region == 2
                        else 'fracture' if region == 4 else 'sunset' if region == 5
                        else 'snow')
                if region == 4 and rect in ledges:
                    kind = 'crumble'
                self.platform_kinds[tuple(rect)] = kind
                if rect in grounds:
                    variant = 'ground'
                elif rect.width <= 130:
                    variant = 'thin'
                else:
                    variant = 'normal'
                self.platform_variants[tuple(rect)] = variant
        self.ground_keys = {tuple(p) for p in self.grounds}
        self.validate_platform_layout()
        self.records = ScoreRecords(score_path)
        if progress_path is None and score_path is not None:
            progress_path = Path(score_path).with_name('progress.json')
        self.progress = AdventureSave(progress_path)
        self.score_ui = ScoreUI()
        self.reset()

    def reset(self):
        if hasattr(self,'score'):
            self.save_score()
        self.score_ui.close()
        self.player_name = self.records.name
        self.run_id = uuid4().hex
        self.exit_open = False
        self.exit_choice = False
        self.exit_return_paused = False
        self.restart_open = False
        self.restart_choice = False
        self.ending_prompt_open = False
        self.ending_prompt_choice = False
        self.quit_requested = False
        self.web_score_sent = False
        self.coach = Coach()
        self.tutorial = None
        self.cave_expedition = None
        self.animation.reset()
        self.feedback.reset()
        self.combat.reset()
        self.companion.reset()
        self.player = pg.Rect((55, 498), NORMAL_PLAYER_SIZE)
        self.x, self.y = float(self.player.x), float(self.player.y)
        self.velocity_y = 0.0
        self.jump_hold = 0.0
        self.coyote_time = COYOTE_TIME
        self.jump_buffer = 0.0
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
        self.max_score = sum(FISH_TYPES[kind] for kind, rect in self.fish)
        self.enemies = []
        for region, kinds in enumerate([('crab','seal'), ('seal','spirit'), ('spirit','spirit'),
                                       ('skua','skua'), ('spirit','seal'), ('crab','skua')]):
            for index, kind in enumerate(kinds):
                platform = (self.region_ledges[region][1] if index and kind == 'spirit'
                            else self.region_grounds[region][0 if index else -1])
                if region == 2 and kind == 'spirit':
                    platform = self.region_ledges[region][index]
                if region == 4 and kind == 'spirit':
                    platform = self.region_grounds[region][0]
                if index and kind == 'seal':
                    platform = self.region_grounds[region][min(1,len(self.region_grounds[region])-1)]
                enemy = Enemy(platform, 55+region*7, kind)
                enemy.uid = f'{region}-{index}-{kind}'
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
        self.last_hit_enemy = None
        self.grow_guard = 0.0
        self.camera_x = 0
        self.display_region = 0
        self.region_banner = 0.0
        self.started = False
        self.falls = 0
        self.won = False
        self.ending_type = 0
        self.ending_completed = False
        self.finish_open = False
        self.game_over = False
        self.ending = None
        self.lives = STARTING_LIVES
        self.time_bonus = 0
        self.time = 0.0
        self.region_fish_rewarded = set()
        self.boss_intro = None
        self.effects = {kind: 0.0 for kind in ITEM_STYLE}
        self.items = []
        # Five spaced pickups; control-changing potions sit on optional upper paths.
        placements = [('grow',0,False,0,120), ('speed',1,True,0,95),
                      ('shield',2,True,-1,105), ('speed',3,True,-1,100),
                      ('grow',5,True,1,90)]
        self.checkpoints = [pg.Rect(grounds[0].left + 30, grounds[0].top-60, 95, 60)
                            for grounds in self.region_grounds]
        self.checkpoint_index = 0
        self.visited_checkpoints = {0}
        self._checkpoint_contact = None
        self.spawn = (55, 498)
        self.crumbles = {}  # key -> (elapsed since stepped on, time left hidden)
        self.caves = [{'rect': pg.Rect(self.region_grounds[i][-1].right - 210, self.region_grounds[i][-1].top-130, 180, 130),
                       'found': False, 'treasure': False} for i in (2, 4)]
        self.babies = []
        for region in (1, 3, 5):
            platform = min(self.region_ledges[region], key=lambda p:p.y)
            self.babies.append({'rect': pg.Rect(platform.right - 40, platform.top - 31, 24, 31),
                                'rescued': False})
        self.carried_baby = None
        self.rescued = 0
        self.in_sanctuary = False
        self.sanctuary_seen = False
        self.max_score += len(self.babies) * 100 + len(self.caves) * 100
        self.content = AdventureContent(self)
        # Fit the seal arena into the open floor between the climbing route
        # and the exit ledges. Deriving it from terrain keeps the lane clear
        # when the world scale changes.
        cave_offset = 2*REGION_WIDTH
        cave_ledges = self.region_ledges[2]
        left_route_edge = max(p.right for p in cave_ledges if p.left < cave_offset+REGION_WIDTH//2)
        exit_route_edge = min(p.left for p in cave_ledges if p.left > cave_offset+REGION_WIDTH//2)
        boss_left = left_route_edge+28
        boss_right = exit_route_edge-28
        boss_arena = pg.Rect(boss_left, 350, boss_right-boss_left, 200)
        self.boss = SealBoss(boss_arena, self.region_grounds[2][0].top,
                             self.boss_images)
        moved = 0
        for _kind, rect in self.fish:
            if rect.colliderect(self.boss.arena):
                rect.centerx = 2*REGION_WIDTH+230+moved*125
                moved += 1
        self.max_score += self.boss.SCORE
        skua_ground = self.region_grounds[4][-1]
        skua_right_ledges = [p for p in self.region_ledges[4]
                             if p.left > skua_ground.left]
        skua_right = min(p.left for p in skua_right_ledges)-28
        skua_arena = pg.Rect(skua_ground.left+30, 330,
                             skua_right-skua_ground.left-30,
                             skua_ground.top-330)
        self.skua_boss = SkuaBoss(skua_arena, skua_ground.top,
                                  self.skua_boss_images)
        moved = 0
        for _kind, rect in self.fish:
            if rect.colliderect(self.skua_boss.arena):
                rect.centerx = self.region_grounds[4][0].left+80+moved*115
                moved += 1
        self.max_score += self.skua_boss.SCORE
        self.max_score += len(REGIONS) * 75  # Complete every region's fish set.
        self.max_score += 6*60 + 170 + 200 + 6*40 + 500 + 225
        self.max_score += 300 + 2*(30+50) + TIME_BONUS_MAX # Caverns, guardians and time bonus.
        self.arrange_potions(placements)
        self.life_items = []
        for region, ledge_index in ((2, -1), (4, 2)):
            platform = self.region_ledges[region][ledge_index]
            self.life_items.append(pg.Rect(platform.left+18,
                                           platform.top-38, 32, 38))
        self.separate_enemy_spawns()
        # Pause state
        self.paused = False

    def make_life_item_image(self):
        """Create a readable extra-life pickup from the companion artwork."""
        surface = pg.Surface((32, 38), pg.SRCALPHA)
        pg.draw.ellipse(surface, (255, 220, 105, 105), (1, 4, 30, 30))
        pg.draw.ellipse(surface, (255, 245, 183), (4, 7, 24, 24), 2)
        penguin = pg.transform.smoothscale(self.baby_image, (22, 28))
        surface.blit(penguin, penguin.get_rect(midbottom=(16, 35)))
        pg.draw.circle(surface, (255, 255, 238), (8, 7), 2)
        return surface

    def separate_enemy_spawns(self):
        """Keep the initial frame readable without changing enemy patrol routes."""
        pickups = [rect for _kind, rect in self.fish+self.items] + self.life_items
        pickups += [baby['rect'] for baby in self.babies]
        for enemy in self.enemies:
            if not any(enemy.rect.colliderect(rect) for rect in pickups):
                continue
            last = max(enemy.left, enemy.right-enemy.rect.width)
            candidates = list(range(enemy.left, last+1, 24))
            if not candidates or candidates[-1] != last:
                candidates.append(last)
            candidates.sort(key=lambda x: abs(x-enemy.rect.x))
            for x in candidates:
                trial = enemy.rect.copy()
                trial.x = x
                if any(trial.inflate(18, 8).colliderect(rect) for rect in pickups):
                    continue
                enemy.rect.x = x
                enemy.x = float(x)
                break

    def start(self, practice=True, guidance=True):
        self.progress.clear()
        self.started = True
        self.coach.enabled = practice or guidance
        if practice:
            self.tutorial = TutorialStage(self)
        else:
            self.region_banner = 2.4
            if guidance:
                self.coach.explain('move')

    def continue_adventure(self):
        if not self.progress.available:
            return False
        self.reset()
        if self.progress.load_into(self):
            self.content.say('체크포인트에서 모험을 이어갑니다.')
            return True
        self.reset()
        return False

    def finish_tutorial(self):
        learned = self.coach.seen.copy()
        self.reset()
        self.started = True
        self.coach.enabled = True
        self.coach.seen = learned
        self.region_banner = 2.4

    def ending_result(self):
        fish_complete = not self.fish
        friends_complete = self.rescued == len(self.babies)
        treasure_complete = all(cave['treasure'] for cave in self.caves)
        if fish_complete and friends_complete and treasure_complete:
            return 4
        if fish_complete and friends_complete:
            return 3
        if fish_complete:
            return 2
        return 1

    def ending_name(self):
        return ENDING_NAMES[max(1, self.ending_type)-1]

    def ending_preview_name(self):
        return ENDING_NAMES[self.ending_result()-1]

    @property
    def ending_unlocked(self):
        return len(self.checkpoints)-1 in self.visited_checkpoints

    def confirm_ending(self):
        self.ending_prompt_open = False
        self.won = True
        self.ending_type = self.ending_result()
        if not self.ending_completed:
            self.time_bonus = max(0, TIME_BONUS_MAX-round(self.time*TIME_BONUS_RATE))
            self.score += self.time_bonus
            self.ending_completed = True
        self.finish_open = True
        self.audio.play('ending')
        self.save_score()

    def continue_collecting(self):
        self.ending_prompt_open = False
        self.ending_prompt_choice = False

    def cycle_quality(self, step=1):
        self.quality_index = (self.quality_index + step) % len(self.quality_levels)
        self.adaptive_quality_index = len(self.quality_levels)-1
        labels = {'performance':'성능', 'balanced':'균형', 'high':'고화질'}
        self.content.say('그래픽 품질 · '+labels[self.quality])
        return self.quality

    def handle_key(self, key):
        # Keep pause controls isolated from normal gameplay input.
        if getattr(self, 'paused', False):
            if self.exit_open:
                if key in (pg.K_ESCAPE, pg.K_n, pg.K_q):
                    self.cancel_exit()
                elif key in (pg.K_LEFT, pg.K_RIGHT, pg.K_TAB):
                    self.exit_choice = not self.exit_choice
                elif key == pg.K_y:
                    self.quit_requested = True
                elif key in (pg.K_RETURN, pg.K_SPACE):
                    if self.exit_choice:
                        self.quit_requested = True
                    else:
                        self.cancel_exit()
                return False
            if key in (pg.K_p, pg.K_ESCAPE):
                self.paused = False
                self.content.say('계속')
                return False
            if key == pg.K_m:
                enabled = self.audio.toggle()
                self.content.say('소리 켜짐' if enabled else '음소거')
                return False
            if key in (pg.K_LEFT, pg.K_DOWN):
                volume = self.audio.change_master_volume(-0.1)
                self.content.say(f'음량 {round(volume*100)}%')
                return False
            if key in (pg.K_RIGHT, pg.K_UP):
                volume = self.audio.change_master_volume(0.1)
                self.content.say(f'음량 {round(volume*100)}%')
                return False
            if key in (pg.K_F6, pg.K_g):
                self.cycle_quality()
                return False
            if key == pg.K_r:
                self.paused = False
                self.ask_restart()
                return False
            if key == pg.K_q:
                self.ask_exit()
                return False
            return False

        if (key in (pg.K_p, pg.K_ESCAPE) and self.started
                and not (self.exit_open or self.restart_open
                         or self.ending_prompt_open or self.ending)
                and not self.score_ui.open):
            self.paused = True
            self.content.say('일시정지')
            return False
        if key == pg.K_m:
            enabled = self.audio.toggle()
            self.content.say('소리 켜짐' if enabled else '소리 꺼짐')
            return False
        if key == pg.K_F6:
            self.cycle_quality()
            return False
        if self.exit_open:
            if key in (pg.K_ESCAPE,pg.K_n):
                self.exit_open = False
            elif key in (pg.K_LEFT,pg.K_RIGHT,pg.K_TAB):
                self.exit_choice = not self.exit_choice
            elif key == pg.K_y:
                self.quit_requested = True
            elif key in (pg.K_RETURN,pg.K_SPACE):
                if self.exit_choice:
                    self.quit_requested = True
                else:
                    self.exit_open = False
            return False
        if self.restart_open:
            if key in (pg.K_ESCAPE, pg.K_n, pg.K_r):
                self.restart_open = False
            elif key in (pg.K_LEFT, pg.K_RIGHT, pg.K_TAB):
                self.restart_choice = not self.restart_choice
            elif key == pg.K_y:
                self.confirm_restart()
            elif key in (pg.K_RETURN, pg.K_SPACE):
                if self.restart_choice:
                    self.confirm_restart()
                else:
                    self.restart_open = False
            return False
        if self.ending_prompt_open:
            if key in (pg.K_ESCAPE, pg.K_n):
                self.continue_collecting()
            elif key in (pg.K_LEFT, pg.K_RIGHT, pg.K_TAB):
                self.ending_prompt_choice = not self.ending_prompt_choice
            elif key == pg.K_y:
                self.confirm_ending()
            elif key in (pg.K_RETURN, pg.K_SPACE):
                if self.ending_prompt_choice:
                    self.confirm_ending()
                else:
                    self.continue_collecting()
            return False
        if self.score_ui.key(self,key):
            return False
        if key == pg.K_ESCAPE:
            # On the title screen ESC still offers a safe exit. During play it
            # is handled above and opens the fully interactive game menu.
            self.ask_exit()
            return False
        if key == pg.K_r and self.started:
            self.ask_restart()
            return False
        if self.game_over:
            if key == pg.K_RETURN:
                self.reset()
                self.start(False)
            return False
        if self.ending:
            if key in (pg.K_RETURN, pg.K_SPACE):
                action = self.ending.advance()
                self.ending = None
                self.finish_open = False
                if action == 'restart':
                    self.reset()
                    self.start(False)
                elif action == 'records':
                    self.won = False
                    self.score_ui.mode = 'ranking'
                    self.score_ui.recent = False
                    self.score_ui.page = 0
                else:
                    self.won = False
            elif key == pg.K_RIGHT:
                self.ending.forward()
            elif key == pg.K_LEFT:
                self.ending.back()
            return False
        if not self.started:
            if key == pg.K_c and self.progress.available:
                self.continue_adventure()
            elif key in (pg.K_RETURN,pg.K_SPACE,pg.K_t):
                self.start(True)
            elif key == pg.K_n:
                self.start(False)
            elif key == pg.K_g:
                self.start(False, False)
            return False
        if key == pg.K_n and self.tutorial:
            self.finish_tutorial()
            self.coach.explain('move')
            return False
        if self.coach.modal:
            if key in (pg.K_RETURN,pg.K_SPACE):
                self.coach.modal = None
                if self.tutorial and self.tutorial.finished:
                    self.finish_tutorial()
            return False
        if self.cave_expedition:
            if key == pg.K_TAB:
                self.content.book_open = not self.content.book_open
            elif key == pg.K_e:
                if self.content.book_open:
                    self.content.book_open = False
                else:
                    self.cave_expedition.action(self)
            elif self.content.book_open and key in (pg.K_LEFT,pg.K_RIGHT):
                self.content.book_page = (self.content.book_page+(1 if key==pg.K_RIGHT else -1))%7
            return key in (pg.K_SPACE,pg.K_UP,pg.K_w) and not self.content.book_open
        if self.tutorial:
            self.tutorial.key(self,key)
            return key in (pg.K_SPACE,pg.K_UP,pg.K_w) and not self.content.book_open
        if key == pg.K_TAB:
            if not self.content.book_open and self.coach.explain('book'):
                return False
            self.content.book_open = not self.content.book_open
        elif key == pg.K_e:
            self.finish_open = False
            if (not self.content.book_open and self.ending_unlocked
                    and self.content.nearby(self,self.checkpoints[-1])):
                self.ending_prompt_open = True
                self.ending_prompt_choice = False
            else:
                self.content.action(self)
        elif key == pg.K_f and self.content.nearby(self,self.checkpoints[-1]):
            self.finish_open = False
            self.content.action(self)
        elif key == pg.K_RETURN and self.won:
            self.finish_open = False
            self.ending = EndingSequence(self.ending_type)
        elif self.content.book_open and key in (pg.K_LEFT,pg.K_RIGHT,pg.K_a,pg.K_d):
            self.content.book_page = (self.content.book_page+(1 if key in (pg.K_RIGHT,pg.K_d) else -1))%7
        elif key == pg.K_x and (self.boss.active or self.skua_boss.active):
            if self.skua_boss.active and self.skua_boss.kick(self.player, self.facing_right):
                self.audio.play('item')
                self.feedback.emit(self.player.midtop, '눈덩이 반격!',
                                   (255, 224, 112))
            elif self.boss.active and self.boss.launch_ice(self.player, self.facing_right):
                self.audio.play('item')
                self.feedback.emit(self.player.midtop, '얼음 조각 투척!',
                                   (174, 235, 249))
            else:
                self.content.say('빙벽 충돌 뒤 얼음 조각을 얻을 수 있어요.')
            return False
        elif key in (pg.K_SPACE,pg.K_UP,pg.K_w):
            return not self.content.diving and not self.content.book_open and not self.coach.explain('jump')
        return False

    def ask_exit(self):
        if not self.exit_open:
            self.exit_return_paused = bool(getattr(self, 'paused', False))
            self.paused = True
            self.exit_open = True
            self.exit_choice = False

    def cancel_exit(self):
        self.exit_open = False
        self.paused = bool(getattr(self, 'exit_return_paused', False))

    def ask_restart(self):
        if not self.restart_open:
            self.restart_open = True
            self.restart_choice = False

    def confirm_restart(self):
        self.progress.clear()
        self.reset()

    def handle_click(self, pos):
        if getattr(self, 'paused', False):
            if self.exit_open:
                cancel, confirm = self.ui.exit_buttons()
                if cancel.collidepoint(pos):
                    self.cancel_exit()
                elif confirm.collidepoint(pos):
                    self.quit_requested = True
                return
            resume, restart, quitb = self.ui.pause_buttons()
            mute, quieter, louder = self.ui.pause_audio_buttons()
            quality_buttons = self.ui.pause_quality_buttons()
            if mute.collidepoint(pos):
                enabled = self.audio.toggle()
                self.content.say('소리 켜짐' if enabled else '음소거')
                return
            if quieter.collidepoint(pos):
                volume = self.audio.change_master_volume(-0.1)
                self.content.say(f'음량 {round(volume*100)}%')
                return
            if louder.collidepoint(pos):
                volume = self.audio.change_master_volume(0.1)
                self.content.say(f'음량 {round(volume*100)}%')
                return
            for index, button in enumerate(quality_buttons):
                if button.collidepoint(pos):
                    self.quality_index = index
                    self.adaptive_quality_index = len(self.quality_levels)-1
                    self.cycle_quality(0)
                    return
            if resume.collidepoint(pos):
                self.paused = False
                self.content.say('계속')
                return
            if restart.collidepoint(pos):
                self.paused = False
                self.ask_restart()
                return
            if quitb.collidepoint(pos):
                self.ask_exit()
                return
            return
        if self.exit_open:
            cancel,confirm = self.ui.exit_buttons()
            if cancel.collidepoint(pos):
                self.exit_open = False
            elif confirm.collidepoint(pos):
                self.quit_requested = True
            return
        if self.restart_open:
            cancel, confirm = self.ui.restart_buttons()
            if cancel.collidepoint(pos):
                self.restart_open = False
            elif confirm.collidepoint(pos):
                self.confirm_restart()
            return
        if self.ending_prompt_open:
            collect, ending = self.ui.ending_prompt_buttons()
            if collect.collidepoint(pos):
                self.continue_collecting()
            elif ending.collidepoint(pos):
                self.confirm_ending()
            return
        if self.ending:
            for index, rect in enumerate(self.ending.buttons()):
                if rect.collidepoint(pos):
                    self.ending.choice = index
                    self.handle_key(pg.K_RETURN)
                    break
            return
        if self.score_ui.click(self,pos):
            return
        if not self.started:
            for action, rect, _label in self.ui.intro_buttons(self):
                if not rect.collidepoint(pos):
                    continue
                if action == 'tutorial':
                    self.start(True)
                elif action == 'skip':
                    self.start(False)
                elif action == 'quiet':
                    self.start(False, False)
                elif action == 'continue':
                    self.continue_adventure()
                return

    def save_score(self):
        if not getattr(self,'started',False) or self.tutorial or self.score<=0:
            return True
        entry = {'run':self.run_id,'name':self.player_name,'score':self.score,
                 'fish':self.total-len(self.fish),'rescued':self.rescued,
                 'seconds':round(self.time),'cleared':self.won,
                 'ending':self.ending_type,
                 'date':datetime.now().isoformat(timespec='seconds')}
        saved = self.records.record(entry)
        # The web page owns authentication and sends the record with its
        # same-origin session cookie. A run id makes retries idempotent.
        completed = self.won or self.game_over
        if completed and not self.web_score_sent and sys.platform == 'emscripten':
            try:
                import platform
                message = json.dumps({'type':'penguin-score','record':entry})
                platform.window.parent.postMessage(message, platform.window.location.origin)
                self.web_score_sent = True
            except Exception:
                # Keep the ending playable if the host page is unavailable.
                pass
        return saved

    def explain_nearby(self, slide):
        if slide and self.coach.explain('slide'):
            return
        if self.content.nearby(self,self.checkpoints[-1]):
            self.coach.explain('home')
        elif self.content.escape_start <= self.player.centerx <= self.content.escape_start+130 and not self.content.escape_cleared:
            self.coach.explain('escape')
        elif self.content.context(self):
            self.coach.explain('interact')

    def potion_obstacles(self):
        obstacles = [rect for kind, rect in self.fish]
        obstacles += [self.igloo_image.get_rect(midbottom=r.midbottom) for r in self.checkpoints]
        obstacles += [self.cave_image.get_rect(midbottom=c['rect'].midbottom) for c in self.caves]
        obstacles += [self.baby_image.get_rect(midbottom=b['rect'].midbottom) for b in self.babies]
        obstacles += [j['rect'] for j in self.content.journals] + [self.content.hole, self.content.lever]
        obstacles += [c['rect'] for c in self.content.crystals]
        for enemy in self.enemies:
            # Reserve the full patrol plus enough reaction room for a player who
            # has just collected a potion. This also covers seal charges, spirit
            # jumps and the skua's vertical flight arc.
            vertical = 95 if enemy.kind in ('skua', 'spirit') else 38
            patrol = pg.Rect(enemy.left, enemy.base_y-vertical,
                             enemy.right-enemy.left,
                             enemy.rect.height+vertical*2)
            obstacles.append(patrol.inflate(440, 24))
        return obstacles

    def arrange_potions(self, placements):
        """Reserve room for bobbing sprites and the entire enemy patrol route."""
        self.items = []
        obstacles = self.potion_obstacles()
        for kind, region, upper, index, shift in placements:
            preferred = (self.region_ledges if upper else self.region_grounds)[region][index]
            alternatives = self.region_ledges[region] if upper else self.region_grounds[region] + self.region_ledges[region]
            for platform in [preferred] + [p for p in alternatives if p != preferred]:
                positions = range(platform.left+18, platform.right-47, 8)
                for x in sorted(positions, key=lambda x: abs(x-(preferred.x+shift))):
                    rect = pg.Rect(x, platform.top-36, 30, 36)
                    if not any(rect.inflate(28, 18).colliderect(o) for o in obstacles):
                        self.items.append((kind, rect))
                        obstacles.append(rect.inflate(12, 12))
                        break
                else:
                    continue
                break
            else:
                raise ValueError('No clear potion position in region ' + str(region))

    def platform_draw_rect(self, platform):
        rect = platform.move(-self.camera_x, 0)
        elapsed, hidden = self.crumbles.get(tuple(platform), (0, 0))
        if elapsed and not hidden:
            progress = min(1, elapsed / 0.8)
            rect.move_ip(round(math.sin(elapsed*65)*(1+progress*4)),
                         round(math.sin(elapsed*47)*(1+progress*2)))
        return rect

    def ground_join_sides(self, platform):
        """Return edges that continue into neighbouring ground at the same height."""
        if tuple(platform) not in self.ground_keys:
            return False, False
        left_join = any(other is not platform and other.top == platform.top
                        and abs(other.right-platform.left) <= 2 for other in self.grounds)
        right_join = any(other is not platform and other.top == platform.top
                         and abs(other.left-platform.right) <= 2 for other in self.grounds)
        return left_join, right_join

    def validate_platform_layout(self):
        """Reject accidental overlaps while allowing edges to meet exactly."""
        for index, platform in enumerate(self.platforms):
            for other in self.platforms[index+1:]:
                if platform.colliderect(other):
                    raise ValueError(f'Overlapping platforms: {platform} / {other}')

    def platform_texture(self, kind, size, ground=False, joins=(False, False),
                         variant='normal'):
        """Build a calm, readable ice shelf with minimal repeated detail."""
        if ground:
            variant = 'ground'
        key = (kind, size, ground, joins, variant)
        if key not in self.platform_textures:
            width, height = size
            profile_heights = {'thin': 30, 'normal': 38, 'ground': 50}
            visual_height = max(height, profile_heights.get(variant, 64))
            # Platforms are solid scenery.  A surface without per-pixel alpha
            # prevents decorative shading from punching translucent lines or
            # panels through the body.
            surface = pg.Surface((width, visual_height)).convert()
            cap, body, shadow = self.platform_palettes[kind]
            dip = 10 if ground else 9
            # The collision rectangle and artwork share one solid silhouette.
            # This keeps the shelf readable and avoids holes at its lower
            # corners when several pieces form a continuous route.
            surface.fill((*body[:3], 255))
            pg.draw.rect(surface, (*shadow[:3], 255),
                         (0, 0, width, visual_height), 2)
            inner_top = min(visual_height-3, dip+7)
            pg.draw.rect(surface, (*cap[:3], 42),
                         (3, inner_top, max(1, width-6),
                          max(1, visual_height-inner_top-3)))
            pg.draw.line(surface, (*shadow, 70),
                         (4, min(visual_height-3, inner_top+11)),
                         (width-5, min(visual_height-3, inner_top+9)), 1)
            profiles = {
                'snow': (0, 2, 1, 3), 'ice': (1, 4, 0, 2),
                'cave': (3, 1, 4, 2), 'fracture': (2, 5, 1, 4),
                'crumble': (4, 2, 5, 1), 'sunset': (1, 3, 2, 4),
            }
            q1, mid, q3, end = profiles[kind]
            cap_points = [(0, 0), (width, 0), (width, dip-2+end),
                          (width*3//4, dip+q3), (width//2, dip-1+mid),
                          (width//4, dip+q1), (0, dip-2+end)]
            pg.draw.polygon(surface, cap, cap_points)
            pg.draw.lines(surface, (255, 255, 255, 190), False,
                          [(2, 1), (width//2, 2), (width-3, 1)], 2)
            pg.draw.lines(surface, shadow, False,
                          [(0, dip-2), (width//4, dip+1),
                           (width//2, dip-1), (width, dip-2)], 2)
            if not ground:
                # Subtle end brackets echo the solid beam construction in the
                # reference while preserving the game's ice palette.
                bracket_width = min(5, max(3, width//28))
                pg.draw.rect(surface, (*shadow[:3], 190),
                             (1, dip, bracket_width, visual_height-dip-1))
                pg.draw.rect(surface, (*shadow[:3], 190),
                             (width-bracket_width-1, dip, bracket_width,
                              visual_height-dip-1))
            band_y = min(visual_height-4, dip+5)
            facet_count = min(2, max(1, width//190))
            for facet in range(facet_count):
                center = (facet+1)*width//(facet_count+1)
                bottom = min(visual_height-4, band_y+9+(facet%2)*5)
                pg.draw.lines(surface, (*shadow, 105), False,
                              [(center, band_y), (center-4, bottom-3),
                               (center+2, bottom)], 1)
            # One broad seam per long shelf adds depth without a noisy pattern.
            if width >= 145:
                seam_x = width // 2 + (17 if width % 3 else -19)
                seam_bottom = min(visual_height-3, 24 if ground else visual_height-5)
                pg.draw.lines(surface, (*shadow, 135), False,
                              [(seam_x, 12), (seam_x-5, 18),
                               (seam_x+2, seam_bottom)], 1)
            # Distinct geology makes each region readable at a glance while
            # preserving the solid collision-aligned silhouette.
            detail_y = min(visual_height-5, dip+12)
            if kind == 'snow':
                for x in range(18, width, 42):
                    pg.draw.arc(surface, (255,255,255),
                                (x-11, 2, 22, 9), math.pi, math.tau, 2)
            elif kind == 'ice':
                for x in range(24, width, 55):
                    pg.draw.lines(surface, cap, False,
                                  [(x, detail_y+8), (x+9, detail_y-3),
                                   (x+18, detail_y+7)], 2)
            elif kind == 'cave':
                for y in range(detail_y, visual_height-4, 11):
                    offset = 12 if (y//11)%2 else 0
                    pg.draw.line(surface, shadow, (4, y), (width-5, y), 1)
                    for x in range(offset+28, width, 62):
                        pg.draw.line(surface, shadow, (x, y),
                                     (x-4, min(visual_height-3, y+7)), 1)
            elif kind in ('fracture', 'crumble'):
                crack_color = (108,91,169) if kind == 'crumble' else shadow
                for x in range(32, width, 74):
                    pg.draw.lines(surface, crack_color, False,
                                  [(x, 4), (x-6, detail_y),
                                   (x+4, min(visual_height-3, detail_y+10))], 2)
            elif kind == 'sunset':
                pg.draw.line(surface, (255,218,207), (5, detail_y),
                             (width-6, max(3, detail_y-2)), 2)
                for x in range(26, width, 64):
                    pg.draw.circle(surface, cap, (x, detail_y+9), 3)
            self.platform_textures[key] = surface
        return self.platform_textures[key]
    def draw_background(self, screen):
        drift = round(400 * max(0, min(1, self.camera_x / (WORLD_WIDTH-WIDTH))))
        weights = self.scene_weights()
        if self.quality == 'performance' and len(weights) == 2:
            # Feather the low-cost wipe in narrow strips. This avoids a full
            # screen alpha blend in WebAssembly without exposing a hard seam.
            left_region = weights[0][0]
            right_region, progress = weights[1]
            screen.blit(self.scene_backgrounds[left_region], (-drift, 0))
            reveal = round((WIDTH+180)*progress)
            if reveal:
                old_clip = screen.get_clip()
                edge = WIDTH+90-reveal
                feather = 150
                solid_left = max(0, min(WIDTH, edge+feather//2))
                if solid_left < WIDTH:
                    screen.set_clip(pg.Rect(solid_left, 0, WIDTH-solid_left, HEIGHT))
                    screen.blit(self.scene_backgrounds[right_region], (-drift, 0))
                transition_left = max(0, edge-feather//2)
                transition_right = min(WIDTH, edge+feather//2)
                strips = 6
                for band in range(strips):
                    x0 = round(transition_left+(transition_right-transition_left)*band/strips)
                    x1 = round(transition_left+(transition_right-transition_left)*(band+1)/strips)
                    if x1 <= x0:
                        continue
                    background = self.scene_backgrounds[right_region]
                    background.set_alpha(round(255*(band+1)/(strips+1)))
                    screen.set_clip(pg.Rect(x0, 0, x1-x0, HEIGHT))
                    screen.blit(background, (-drift, 0))
                    background.set_alpha(None)
                screen.set_clip(old_clip)
            return
        for index, (region, weight) in enumerate(weights):
            background = self.scene_backgrounds[region]
            if index:
                background.set_alpha(round(255*weight))
            screen.blit(background, (-drift, 0))
            if index:
                background.set_alpha(None)

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
        if self.boss_intro:
            self.boss_intro['time'] = max(0, self.boss_intro['time']-dt)
            if not self.boss_intro['time']:
                self.boss_intro = None
        if region != self.display_region:
            self.display_region = region
            self.region_banner = 2.4

    def update_adventure(self, dt):
        sanctuary = self.player.colliderect(self.checkpoints[-1].inflate(90,60))
        if sanctuary:
            self.invincible = max(self.invincible,0.15)
            if not self.sanctuary_seen:
                self.feedback.emit(self.player.midtop,'보금자리의 안전지대',(160,239,193))
                self.sanctuary_seen = True
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
        touching_checkpoint = False
        for index, checkpoint in enumerate(self.checkpoints):
            if self.player.colliderect(checkpoint):
                touching_checkpoint = True
                first_visit = index not in self.visited_checkpoints
                if first_visit:
                    self.visited_checkpoints.add(index)
                    self.audio.play('checkpoint')
                    if index == len(self.checkpoints)-1:
                        self.content.say('엔딩 해금! 마지막 이글루 근처에서 E로 모험 마무리')
                self.checkpoint_index = index
                self.spawn = self.checkpoint_spawn(index)
                if self.carried_baby is not None:
                    self.babies[self.carried_baby]['rescued'] = True
                    self.carried_baby = None
                    self.companion.reset()
                    self.rescued += 1
                    self.score += 100
                    self.audio.play('rescue')
                    self.feedback.emit(checkpoint.midtop, '친구 구조! +100', (157,238,183))
                if self._checkpoint_contact != index:
                    saved = self.progress.save(self)
                    if first_visit or not saved:
                        self.feedback.emit(checkpoint.midtop,
                                           '저장 완료' if saved else '저장 실패',
                                           (169,235,255) if saved else (255,170,150))
                self._checkpoint_contact = index
                break
        if not touching_checkpoint:
            self._checkpoint_contact = None
        for index, baby in enumerate(self.babies):
            if (not baby['rescued'] and self.carried_baby is None
                    and self.content.quests[index]
                    and self.player.colliderect(baby['rect'])):
                self.carried_baby = index
                self.companion.start(self, baby)
                self.feedback.emit(baby['rect'].midtop, '이글루로 데려가요!', (178,227,255))
        for cave in self.caves:
            if self.player.colliderect(cave['rect']):
                cave['found'] = True

    def checkpoint_spawn(self, index):
        """Return a standing-height spawn anchored to the checkpoint's ground."""
        checkpoint = self.checkpoints[index]
        x = checkpoint.x + 25
        supports = [ground for ground in self.grounds
                    if ground.left <= x and x + NORMAL_PLAYER_SIZE[0] <= ground.right]
        ground = min(supports, key=lambda rect: abs(rect.top-checkpoint.bottom))
        return (x, ground.top-NORMAL_PLAYER_SIZE[1])

    def safe_respawn_position(self):
        """Repair legacy or crouched spawn coordinates before placing the player."""
        x = max(0, min(WORLD_WIDTH-NORMAL_PLAYER_SIZE[0], int(self.spawn[0])))
        expected_bottom = int(self.spawn[1]) + NORMAL_PLAYER_SIZE[1]
        supports = [ground for ground in self.grounds
                    if ground.left <= x and x + NORMAL_PLAYER_SIZE[0] <= ground.right]
        if not supports:
            return self.checkpoint_spawn(self.checkpoint_index)
        ground = min(supports, key=lambda rect: abs(rect.top-expected_bottom))
        return (x, ground.top-NORMAL_PLAYER_SIZE[1])

    def respawn(self, hit=False):
        self.audio.play('hit' if hit else 'fall')
        if not self.consume_life(hit):
            return
        self.boss.reset_encounter()
        self.skua_boss.reset_encounter()
        self.animation.reset()
        self.feedback.reset()
        self.combat.reset()
        self.companion.reset()
        self.effects = {kind: 0.0 for kind in ITEM_STYLE}
        self.player.size = NORMAL_PLAYER_SIZE
        self.spawn = self.safe_respawn_position()
        self.player.topleft = self.spawn
        self.x, self.y = map(float, self.player.topleft)
        self.velocity_y = 0.0
        self.velocity_x = 0.0
        self.jump_hold = 0.0
        self.jump_buffer = 0.0
        self.coyote_time = COYOTE_TIME
        self.surface_kind = 'snow'
        self.carried_baby = None
        self.content.sliding = False
        self.content.diving = False
        self.content.escape_active = False
        self.crumbles.clear()
        self.on_ground = True
        self.clear_respawn_area()
        self.invincible = RESPAWN_INVINCIBILITY
        self.grow_guard = 0.0
        self.feedback.emit(self.player.midtop, '피격! 저장 지점 복귀' if hit else '저장 지점에서 다시!', (205,235,255))
        self.camera_x = max(0, min(WORLD_WIDTH - WIDTH, self.player.centerx - WIDTH // 2))
        self.display_region = self.player.centerx // REGION_WIDTH
        self.region_banner = 0.0

    def clear_respawn_area(self):
        """Reset enemies that could camp a checkpoint after the player dies."""
        for enemy in self.enemies:
            patrol_left = enemy.left
            patrol_right = enemy.right
            nearest_patrol_x = max(patrol_left, min(self.player.centerx, patrol_right))
            crosses_spawn = abs(nearest_patrol_x-self.player.centerx) < RESPAWN_CLEAR_RADIUS
            currently_near = abs(enemy.rect.centerx-self.player.centerx) < RESPAWN_CLEAR_RADIUS
            caused_hit = enemy is self.last_hit_enemy
            if not currently_near and not crosses_spawn and not caused_hit:
                continue
            left = enemy.left
            right = enemy.right-enemy.rect.width
            target = max((left, right), key=lambda x: abs((x+enemy.rect.width/2)-self.player.centerx))
            enemy.x = float(target)
            enemy.rect.x = round(enemy.x)
            enemy.speed = (-enemy.patrol_speed if enemy.rect.centerx < self.player.centerx
                           else enemy.patrol_speed)
            enemy.warning = 0.0
            enemy.charge = 0.0
            enemy.cooldown = max(enemy.cooldown, 2.0)
            enemy.respawn_safe = max(enemy.respawn_safe, RESPAWN_INVINCIBILITY+1.5)
            enemy.velocity_y = 0.0
            enemy.y = float(enemy.base_y)
            enemy.rect.y = round(enemy.base_y)
            if enemy.kind == 'skua':
                # Start the bird high in its arc as it flies away from the
                # checkpoint, so its first visible pass cannot overlap spawn.
                enemy.clock = 3*math.pi/(2*2.3)
                enemy.rect.y = round(enemy.base_y-28)
            enemy.previous_top = enemy.rect.top
        self.last_hit_enemy = None

    def consume_life(self, hit=False):
        if self.game_over:
            return False
        if hit:
            self.hits += 1
        else:
            self.falls += 1
        self.lives = max(0, self.lives-1)
        if self.lives:
            self.progress.save(self)
            return True
        self.game_over = True
        self.finish_open = False
        self.content.diving = False
        self.content.book_open = False
        self.progress.clear()
        self.save_score()
        return False

    def update(self, dt, direction=0, jump=False, slide=False, swim_vertical=0,
               jump_held=None):
        if (self.exit_open or self.restart_open or self.ending_prompt_open or
                self.quit_requested or self.score_ui.open or self.game_over or
                getattr(self, 'paused', False)):
            return
        if not self.started:
            return
        self.audio.set_scene(self.player.centerx // REGION_WIDTH,
                             underwater=self.content.diving)
        if self.coach.modal:
            return
        if self.ending:
            self.ending.update(dt)
            return
        if self.tutorial:
            self.tutorial.update(self,dt,direction,jump,slide,swim_vertical,jump_held)
            return
        if self.content.book_open:
            return
        if self.cave_expedition:
            self.cave_expedition.update(self,dt,direction,jump,slide,jump_held)
            return
        if not self.content.diving and not self.combat.hurt:
            self.explain_nearby(slide)
            if self.coach.modal:
                return
        if self.won and self.finish_open:
            self.content.notice_left = max(0,self.content.notice_left-dt)
            return
        self.time += dt
        if self.content.diving:
            self.content.swim(self,dt,direction,swim_vertical)
            return
        self.invincible = max(0.0, self.invincible - dt)
        self.grow_guard = max(0.0,self.grow_guard-dt)
        self.feedback.update(dt,self)
        was_hurt = self.combat.hurt > 0
        self.combat.update(dt)
        if was_hurt:
            if not self.combat.hurt:
                self.respawn(hit=True)
            return
        self.content.sliding = bool(slide and self.on_ground and not jump)
        desired_height = 28 if self.content.sliding else 52
        if self.player.height != desired_height:
            feet = self.player.midbottom
            self.player.height = desired_height
            self.player.midbottom = feet
            self.y = float(self.player.y)
        was_grounded = self.on_ground
        if self.on_ground:
            self.coyote_time = COYOTE_TIME
        else:
            self.coyote_time = max(0.0, self.coyote_time-dt)
        if jump:
            self.jump_buffer = JUMP_BUFFER_TIME
        else:
            self.jump_buffer = max(0.0, self.jump_buffer-dt)
        previous_x = self.player.x
        self.update_adventure(dt)
        previous_bottom = self.player.bottom
        for enemy in self.enemies:
            enemy.update(dt, self.player)
        for kind in self.effects:
            previous = self.effects[kind]
            self.effects[kind] = max(0.0, self.effects[kind] - dt)
            if kind=='grow' and previous>0 and self.effects[kind]==0:
                self.invincible = max(self.invincible,GROW_EXIT_INVINCIBILITY)
                self.grow_guard = GROW_EXIT_INVINCIBILITY
                self.feedback.emit(self.player.midtop,'거대 효과 종료 · 보호 1.5초',(159,231,255))
        if self.effects['shield']:
            self.invincible = max(self.invincible, 0.12)
        speed = MOVE_SPEED * (1.6 if self.effects['speed'] else 1.0) * (1.35 if self.content.sliding else 1)
        if self.jump_buffer > 0 and (self.on_ground or self.coyote_time > 0):
            self.velocity_y = JUMP_SPEED
            self.on_ground = False
            self.jump_hold = JUMP_HOLD_TIME
            self.jump_buffer = 0.0
            self.coyote_time = 0.0
            self.audio.play('jump')
        if self.velocity_y < 0 and self.jump_hold > 0:
            if jump_held is True:
                self.velocity_y -= JUMP_HOLD_FORCE * dt
                self.jump_hold = max(0.0, self.jump_hold-dt)
            elif jump_held is False:
                self.velocity_y = max(self.velocity_y, JUMP_RELEASE_SPEED)
                self.jump_hold = 0.0
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
        if self.boss.confine(self.player):
            self.x = float(self.player.x)
            self.velocity_x = 0.0
        if self.skua_boss.confine(self.player):
            self.x = float(self.player.x)
            self.velocity_x = 0.0
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
            # Honor a jump pressed just before touching down. This avoids a
            # dead input frame on narrow platforms and during fast descents.
            if self.jump_buffer > 0:
                self.velocity_y = JUMP_SPEED
                self.on_ground = False
                self.jump_hold = JUMP_HOLD_TIME
                self.jump_buffer = 0.0
                self.coyote_time = 0.0
                self.audio.play('jump')
        boss_event = self.boss.update(dt, self.player)
        if boss_event == 'start':
            self.audio.play('checkpoint')
            self.boss_intro = {'title': '바다표범 보스',
                               'hint': '돌진을 피하고 빙벽 충돌 후 반격',
                               'time': 2.8}
        elif boss_event == 'impact':
            self.audio.play('hit')
            self.feedback.emit(self.boss.rect.midtop, '빙벽 충돌! 지금 공격!', (143, 235, 247))
        elif boss_event in ('ranged_hit', 'ranged_defeat'):
            self.audio.play('defeat')
            # A successful shot can change the boss from stunned to roaring
            # while the player is still beside it. Do not turn that same
            # successful attack into unavoidable contact damage.
            self.invincible = max(self.invincible, 0.55)
            if boss_event == 'ranged_defeat':
                self.score += self.boss.SCORE
                self.feedback.emit(self.boss.rect.midtop,
                                   f'원거리 보스 격파! +{self.boss.SCORE}',
                                   (255, 224, 112))
                self.progress.save(self)
            else:
                self.feedback.emit(self.boss.rect.midtop,
                                   f'얼음 조각 명중 {self.boss.hits}/{self.boss.MAX_HITS}',
                                   (143, 235, 247))
        boss_contact = (self.boss.weakspot() if self.boss.state == 'stunned'
                        else self.boss.rect)
        if self.boss.active and self.player.colliderect(boss_contact):
            can_stomp = self.boss.can_stomp(
                self.player, previous_bottom, self.velocity_y)
            if can_stomp and self.boss.stomp():
                # Place the feet clear of the new roar hitbox before the next
                # frame. The bounce alone left several overlapping frames and
                # caused an immediate retaliatory hit after a valid stomp.
                self.player.bottom = self.boss.rect.top-4
                self.velocity_y = -470
                self.y = float(self.player.y)
                self.on_ground = False
                self.invincible = max(self.invincible, 0.75)
                self.audio.play('defeat')
                if self.boss.defeated:
                    self.score += self.boss.SCORE
                    self.feedback.emit(self.boss.rect.midtop,
                                       f'보스 격파! +{self.boss.SCORE}', (255, 224, 112))
                    self.progress.save(self)
                else:
                    self.feedback.emit(self.boss.rect.midtop,
                                       f'보스 타격 {self.boss.hits}/{self.boss.MAX_HITS}',
                                       (255, 224, 112))
            elif not self.invincible and self.boss.state != 'stunned':
                self.combat.hit(self.player, self.boss)
                self.feedback.emit(self.player.midtop, '보스에게 피격!', (255, 133, 125))
                return
        skua_event = self.skua_boss.update(dt, self.player)
        if self.skua_boss.confine(self.player):
            self.x = float(self.player.x)
            self.velocity_x = 0.0
        if skua_event == 'start':
            self.audio.play('checkpoint')
            self.boss_intro = {'title': '갈매기 대장',
                               'hint': '급강하를 피하고 눈덩이를 X로 반격',
                               'time': 2.8}
        elif skua_event == 'impact':
            self.audio.play('hit')
            self.feedback.emit(self.skua_boss.rect.midtop,
                               '급강하 충돌! 지금 반격하세요!', (174, 235, 249))
        elif skua_event in ('hit', 'defeat'):
            self.audio.play('defeat')
            self.invincible = max(self.invincible, 0.6)
            if skua_event == 'defeat':
                self.score += self.skua_boss.SCORE
                self.feedback.emit(self.skua_boss.rect.midtop,
                                   f'갈매기 보스 격파! +{self.skua_boss.SCORE}',
                                   (255, 224, 112))
                self.progress.save(self)
            else:
                self.feedback.emit(self.skua_boss.rect.midtop,
                                   f'눈덩이 명중 {self.skua_boss.hits}/{self.skua_boss.MAX_HITS}',
                                   (174, 235, 249))
        skua_projectile_hit = (not self.invincible and self.skua_boss.active
                               and self.skua_boss.snowball_hits(self.player))
        skua_body_hit = (not self.invincible and self.skua_boss.can_damage_player()
                         and self.player.colliderect(self.skua_boss.body_hitbox()))
        if skua_projectile_hit or skua_body_hit:
            self.combat.hit(self.player, self.skua_boss)
            self.feedback.emit(self.player.midtop, '갈매기에게 피격!', (255, 133, 125))
            return
        # Descending from above is a stomp; side and upward contact cause damage.
        for enemy in list(self.enemies):
            damage_box = enemy.damage_hitbox()
            stomp_box = enemy.stomp_hitbox()
            can_stomp = (self.velocity_y > 0
                         and previous_bottom <= stomp_box.top+5
                         and self.player.bottom >= stomp_box.top
                         and self.player.right > stomp_box.left
                         and self.player.left < stomp_box.right)
            if not (self.player.colliderect(damage_box) or can_stomp):
                continue
            if enemy.respawn_safe:
                continue
            powered_contact = self.effects['grow'] or self.effects['shield']
            if powered_contact or can_stomp:
                self.enemies.remove(enemy)
                self.combat.defeat(enemy, self.enemy_images)
                self.score += enemy.points
                self.audio.play('defeat')
                self.feedback.emit(enemy.rect.midtop, f'{ENEMY_INFO[enemy.kind][0]} 처치 +{enemy.points}', (255,219,132))
                self.defeated += 1
                if not powered_contact:
                    self.player.bottom = enemy.rect.top
                    self.y = float(self.player.y)
                    self.velocity_y = -420
                    self.on_ground = False
            elif not self.invincible:
                self.last_hit_enemy = enemy
                self.combat.hit(self.player, enemy)
                self.feedback.emit(self.player.midtop, '피격!', (255,153,153))
                return
        remaining_fish = []
        collected_regions = set()
        for kind, rect in self.fish:
            if self.player.colliderect(rect):
                self.score += FISH_TYPES[kind]
                self.content.wallet += 1
                collected_regions.add(min(len(REGIONS)-1, rect.centerx//REGION_WIDTH))
                self.audio.play('collect')
                if kind == 'blue':
                    self.content.wallet += 1
                    detail = ' · 먹이 +2'
                elif kind == 'gold':
                    self.invincible = max(self.invincible, 1.25)
                    detail = ' · 보호 1.2초'
                else:
                    detail = ''
                self.feedback.emit(rect.center, f'+{FISH_TYPES[kind]}{detail}', (255,232,151))
            else:
                remaining_fish.append((kind, rect))
        self.fish = remaining_fish
        for region in collected_regions:
            if (region not in self.region_fish_rewarded
                    and not any(rect.centerx//REGION_WIDTH == region
                                for _kind, rect in self.fish)):
                self.region_fish_rewarded.add(region)
                self.score += 75
                self.feedback.emit(self.player.midtop,
                                   f'{region+1}구역 물고기 완료! +75', (150, 240, 207))
                self.progress.save(self)
        remaining_items = []
        for kind, rect in self.items:
            if not self.player.colliderect(rect):
                remaining_items.append((kind, rect))
            else:
                # Picking the same benefit refreshes it; effects never stack into
                # a confusing combination.
                repeated = self.effects[kind] > 0
                for other in self.effects:
                    self.effects[other] = 0.0
                self.effects[kind] = 6.0 if kind == 'shield' else ITEM_DURATION
                self.audio.play('item')
                name = {'grow':'성장! 적 돌파', 'speed':'가속! 속도 증가',
                        'shield':'보호막! 피해 방지'}[kind]
                if repeated:
                    name = {'grow':'성장', 'speed':'가속',
                            'shield':'보호막'}[kind]+' 시간 갱신'
                self.feedback.emit(rect.center, name, ITEM_STYLE[kind][0],kind=kind)
        self.items = remaining_items
        remaining_lives = []
        for rect in self.life_items:
            if self.player.colliderect(rect) and self.lives < STARTING_LIVES:
                self.lives += 1
                self.audio.play('rescue')
                self.feedback.emit(rect.center, '목숨 회복!',
                                   (255, 225, 117), kind='life')
                self.progress.save(self)
            else:
                remaining_lives.append(rect)
        self.life_items = remaining_lives
        self.content.update(self,dt)
        self.update_adventure(0)
        if self.player.top > HEIGHT:
            self.respawn()
            return
        self.animation.update(dt, self.player, self.velocity_y, self.on_ground,
                              was_grounded, abs(self.player.x-previous_x))
        self.update_presentation(dt)
        self.companion.update(self, dt)

    def draw(self, screen):
        self.draw_scene(screen)
        self.score_ui.draw(self,screen)
        if self.game_over:
            self.ui.game_over(self,screen)
        if self.restart_open:
            self.ui.restart_dialog(self,screen)
        if self.ending_prompt_open:
            self.ui.ending_prompt(self,screen)
        if getattr(self, 'paused', False):
            self.ui.pause_menu(self, screen)

    @property
    def quality(self):
        return self.quality_levels[min(self.quality_index,
                                       self.adaptive_quality_index)]

    def observe_render_time(self, milliseconds):
        """Keep decorative work inside the frame budget without resizing art."""
        if self.render_ms_average <= 0:
            self.render_ms_average = milliseconds
        else:
            self.render_ms_average += (milliseconds-self.render_ms_average)*0.06
        if self.render_ms_average > 14:
            self.adaptive_quality_index = 0
            self.fast_render_frames = 0
        elif self.render_ms_average > 10:
            self.adaptive_quality_index = min(self.adaptive_quality_index, 1)
            self.fast_render_frames = 0
        elif self.render_ms_average < 7:
            self.fast_render_frames += 1
            if self.fast_render_frames >= 180:
                self.adaptive_quality_index = min(2, self.adaptive_quality_index+1)
                self.fast_render_frames = 0
        else:
            self.fast_render_frames = 0

    def visible(self, rect, margin=80):
        return rect.right >= self.camera_x-margin and rect.left <= self.camera_x+WIDTH+margin

    def draw_scene(self, screen):
        if not self.started:
            self.draw_intro(screen)
            return
        if self.ending:
            self.ending.draw(self, screen)
            return
        if self.cave_expedition:
            self.cave_expedition.draw(self,screen)
            if self.content.book_open:
                self.content.draw_book(self,screen)
            self.coach.draw(self,screen)
            return
        if self.tutorial:
            self.tutorial.draw(self,screen)
            self.coach.draw(self,screen)
            return
        if self.content.diving:
            self.content.draw_ocean(self,screen)
            if self.content.book_open:
                self.content.draw_book(self,screen)
            self.coach.draw(self,screen)
            return
        self.draw_background(screen)
        # Show water in the ground gaps so falls are visually clear.
        pg.draw.rect(screen, (24, 88, 130), (0, 550, WIDTH, 50))
        # Entrances are cut into the shelf. The shelf lip drawn next embeds the
        # lower edge instead of letting the cave art float over the platform.
        self.draw_cave_entrances(screen)
        for platform in self.active_platforms():
            if not self.visible(platform, 100):
                continue
            rect = self.platform_draw_rect(platform)
            kind = self.platform_kinds[tuple(platform)]
            ground = tuple(platform) in self.ground_keys
            joins = self.ground_join_sides(platform) if ground else (False, False)
            variant = self.platform_variants[tuple(platform)]
            if not ground:
                shadow = pg.Surface((rect.width, 12), pg.SRCALPHA)
                pg.draw.ellipse(shadow, (18, 55, 78, 35), shadow.get_rect())
                screen.blit(shadow, (rect.x, rect.bottom-3))
            screen.blit(self.platform_texture(kind, platform.size, ground, joins,
                                              variant), rect)
            if kind == 'crumble' and tuple(platform) in self.crumbles:
                progress = min(1, self.crumbles[tuple(platform)][0] / 0.8)
                pg.draw.rect(screen, (245, 92, 125), (rect.x, rect.y-4, int(rect.width*progress), 3))
        self.draw_adventure(screen)
        # Static world props (cages, levers, dive holes and home decorations)
        # belong behind hazards. Drawing them first prevents enemies from being
        # hidden while their collision box can still damage the player.
        self.content.draw_world(self,screen)
        glow = self.collectible_layer
        glow.fill((0, 0, 0, 0))
        for kind, fish in self.fish:
            if self.visible(fish):
                rect = fish.move(-self.camera_x, 0)
                color = {'orange': (255, 174, 82), 'blue': (95, 205, 255),
                         'gold': (255, 224, 105)}[kind]
                pg.draw.ellipse(glow, (*color, 38), rect.inflate(14, 10))
                pg.draw.ellipse(glow, (*color, 95), rect.inflate(6, 3), 1)
        for kind, rect in self.items:
            if self.visible(rect):
                draw_rect = rect.move(-self.camera_x, 0)
                color = ITEM_STYLE[kind][0]
                pg.draw.ellipse(glow, (*color, 45), draw_rect.inflate(16, 12))
                pg.draw.ellipse(glow, (*color, 125), draw_rect.inflate(7, 5), 1)
        screen.blit(glow, (0, 0))
        for index, (kind, fish) in enumerate(self.fish):
            if not self.visible(fish):
                continue
            bob = round(math.sin(self.time * 4 + index) * 3)
            screen.blit(self.art.fish(kind,self.time+index*0.17), fish.move(-self.camera_x, bob))
        for kind, rect in self.items:
            if not self.visible(rect):
                continue
            rect = rect.move(-self.camera_x, 0)
            bob = round(math.sin(self.time*3+rect.x*0.01)*3)
            color = ITEM_STYLE[kind][0]
            pg.draw.ellipse(screen, color, (rect.x+2,rect.bottom-3,26,5),2)
            screen.blit(self.item_images[kind], rect.move(0,bob))
        for index, rect in enumerate(self.life_items):
            if not self.visible(rect):
                continue
            draw_rect = rect.move(-self.camera_x,
                                  round(math.sin(self.time*3.2+index)*4))
            pulse = 3+round((math.sin(self.time*5+index)+1)*2)
            pg.draw.ellipse(screen, (255, 221, 112),
                            draw_rect.inflate(pulse*2, 3).move(0, 5), 2)
            screen.blit(self.life_item_image, draw_rect)
        # Enemies are always above collectibles and scenery so danger remains
        # readable even when patrol routes cross a large decorative sprite.
        for enemy in self.enemies:
            if self.visible(enemy.rect, 120):
                enemy.draw(screen, self.camera_x, self.enemy_images)
        self.boss.draw_terrain(screen, self.camera_x, self.time)
        self.boss.draw(screen, self.camera_x, self.time)
        self.skua_boss.draw_terrain(screen, self.camera_x, self.time)
        self.skua_boss.draw(screen, self.camera_x, self.time)
        image = self.feedback.player_image(self)
        if self.combat.hurt:
            image = self.animation.hurt_image(0.45-self.combat.hurt,self.facing_right)
            image = pg.transform.scale(image,(round(image.get_width()*self.feedback.size_scale),round(image.get_height()*self.feedback.size_scale)))
        image = self.combat.pose(image)
        if self.content.sliding:
            if self.on_ground and abs(self.velocity_x)>40:
                rect = self.player.move(-self.camera_x,0)
                for i in range(3):
                    offset = (self.time*160+i*11)%35
                    side = -1 if self.facing_right else 1
                    pg.draw.circle(screen,(228,246,255),(round(rect.centerx+side*(24+offset)),rect.bottom-3-i*2),max(1,4-i))
        self.feedback.draw_aura(self, screen)
        self.animation.draw_puffs(screen, self.camera_x)
        contact_shadow(screen, self.player.move(-self.camera_x, 0).midbottom,
                       self.player.width,
                       not self.on_ground or self.content.diving)
        if self.combat.hurt or not self.invincible or int(self.time * 10) % 2 == 0:
            rect = self.player.move(-self.camera_x, 0)
            if self.combat.hurt:
                age = 0.45-self.combat.hurt
                rect.move_ip(round(self.combat.hit_direction*math.sin(age/0.45*math.pi)*22),
                             -round(math.sin(age/0.45*math.pi)*15))
            screen.blit(image, image.get_rect(midbottom=rect.midbottom))
        self.companion.draw(self, screen)
        self.combat.draw(self, screen)
        self.draw_region_atmosphere(screen)
        self.draw_baby_markers(screen)
        self.feedback.draw(self, screen)
        if self.boss_intro:
            self.ui.boss_intro(self, screen)
        self.ui.hud(self, screen, REGIONS)
        if self.skua_boss.active and not self.skua_boss.defeated:
            self.skua_boss.draw_hud(self, screen)
        elif self.boss.active and not self.boss.defeated:
            self.boss.draw_hud(self, screen)
        else:
            self.ui.rescue_guide(self,screen)
            self.ui.transition(self, screen, REGIONS)
            self.content.draw_hud(self,screen)
        if self.region_banner > 0 and not (self.boss.active or self.skua_boss.active):
            label = self.region_hint_labels[self.display_region]
            self.ui.panel(screen,(490,149,298,31))
            screen.blit(label,(499,154))
        if self.won and self.finish_open:
            self.ui.finish(self, screen)
        if self.content.book_open:
            self.content.draw_book(self,screen)
        self.coach.draw(self,screen)

    def draw_cave_entrances(self, screen):
        for cave in self.caves:
            if not self.visible(cave['rect'], 220):
                continue
            rect = cave['rect'].move(-self.camera_x, 0)
            self.art.grounded(screen,self.cave_image,rect.midbottom)

    def draw_adventure(self, screen):
        region = min(len(REGIONS) - 1, self.player.centerx // REGION_WIDTH)
        for index, checkpoint in enumerate(self.checkpoints):
            if not self.visible(checkpoint, 140):
                continue
            rect = checkpoint.move(-self.camera_x, 0)
            if index == len(self.checkpoints)-1:
                pg.draw.ellipse(screen,(151,222,190),rect.inflate(70,12),2)
            self.art.grounded(screen,self.igloo_image,rect.midbottom)
            if (index == len(self.checkpoints)-1 and self.ending_unlocked
                    and not self.won):
                badge = pg.Rect(0, 0, self.ending_badge_label.get_width()+22, 29)
                badge.midbottom = (rect.centerx, rect.top-8)
                pg.draw.rect(screen, (18, 61, 78), badge, border_radius=12)
                pg.draw.rect(screen, (170, 237, 225), badge, 2, border_radius=12)
                screen.blit(self.ending_badge_label,
                            self.ending_badge_label.get_rect(center=badge.center))
            if index == self.checkpoint_index:
                pg.draw.circle(screen, (111, 255, 151), (rect.centerx, rect.top-32), 5)
        for index, baby in enumerate(self.babies):
            if not baby['rescued'] and index != self.carried_baby:
                if not self.visible(baby['rect']):
                    continue
                rect = baby['rect'].move(-self.camera_x, 0)
                image = self.art.baby('idle',self.time+index*0.3)
                contact_shadow(screen, rect.midbottom, rect.width)
                screen.blit(image,image.get_rect(midbottom=rect.midbottom))
        snow_weight = dict(self.scene_weights()).get(3, 0)
        if snow_weight > 0:
            snow_count = {'performance':24, 'balanced':40, 'high':65}[self.quality]
            if self.quality == 'performance':
                color = tuple(round(170+(channel-170)*snow_weight)
                              for channel in (238, 249, 255))
                for i in range(snow_count):
                    x = int((i * 137 - self.time * 180) % WIDTH)
                    y = int((i * 83 + self.time * 45) % HEIGHT)
                    pg.draw.line(screen, color, (x, y), (x-12, y+4), 2)
            else:
                snow = self.weather_layer
                snow.fill((0, 0, 0, 0))
                for i in range(snow_count):
                    x = int((i * 137 - self.time * 180) % WIDTH)
                    y = int((i * 83 + self.time * 45) % HEIGHT)
                    pg.draw.line(snow, (238, 249, 255, round(255*snow_weight)),
                                 (x, y), (x-12, y+4), 2)
                screen.blit(snow, (0, 0))

    def rescue_target(self):
        if self.carried_baby is not None:
            return ('home',min(self.checkpoints,key=lambda r:abs(r.centerx-self.player.centerx)))
        waiting = [b['rect'] for b in self.babies if not b['rescued']]
        if waiting:
            return ('baby',min(waiting,key=lambda r:abs(r.centerx-self.player.centerx)+abs(r.centery-self.player.centery)))
        return None

    def objective_target(self):
        """Return one clear next objective for the compact compass card."""
        rescue = self.rescue_target()
        if rescue:
            kind, rect = rescue
            return (kind, rect,
                    '친구를 이글루로' if kind == 'home' else '친구 구조',
                    '가장 가까운 이글루' if kind == 'home' else '지역 임무를 해결하세요')
        bosses = [(self.boss, '바다표범 보스'),
                  (self.skua_boss, '갈매기 보스')]
        pending = [(boss, label) for boss, label in bosses if not boss.defeated]
        if pending:
            boss, label = min(pending,
                              key=lambda item: abs(item[0].arena.centerx-self.player.centerx))
            return ('boss', boss.arena, label, '공격 예고를 보고 반격하세요')
        unopened = [c for c in self.caves if not c['treasure']]
        if unopened:
            cave = min(unopened, key=lambda c: abs(c['rect'].centerx-self.player.centerx))
            return ('cave', cave['rect'], '동굴 보물', '봉인석 3개와 레버 찾기')
        if self.fish:
            _kind, rect = min(self.fish,
                              key=lambda item: abs(item[1].centerx-self.player.centerx))
            return ('fish', rect, '남은 물고기', f'{len(self.fish)}마리 남음')
        return ('home', self.checkpoints[-1], '마지막 이글루', 'E로 엔딩 선택')

    def draw_baby_markers(self, screen):
        visible_babies = []
        for index, baby in enumerate(self.babies):
            if baby['rescued'] or index == self.carried_baby:
                continue
            rect = baby['rect'].move(-self.camera_x, 0)
            if rect.right >= 0 and rect.left <= WIDTH:
                visible_babies.append((index, rect))
        if not visible_babies:
            return
        layer = self.marker_layer
        layer.fill((0, 0, 0, 0))
        for index, rect in visible_babies:
            cx = rect.centerx
            pulse = (math.sin(self.time*3+index)+1)/2
            marker_rows = 40 if self.quality == 'performance' else 60 if self.quality == 'balanced' else 80
            for row in range(marker_rows):
                pg.draw.line(layer,(255,225,114,round((1-row/marker_rows)*45)),
                             (cx-17,rect.bottom-row),(cx+17,rect.bottom-row),1)
            radius = round(19+pulse*7)
            pg.draw.ellipse(layer,(255,231,126,200),(cx-radius,rect.bottom-6,radius*2,12),3)
            y = rect.top-22-round(pulse*7)
            pg.draw.polygon(layer,(255,232,114,245),[(cx-9,y),(cx+9,y),(cx,y+10)])
            pg.draw.polygon(layer,(255,255,245,245),[(cx-5,y+2),(cx+5,y+2),(cx,y+7)])
            for i in range(4):
                phase = self.time*1.5+i*math.pi/2
                x = round(cx+math.cos(phase)*23)
                y = round(rect.centery+math.sin(phase)*23)
                pg.draw.line(layer,(255,244,171,220),(x-3,y),(x+3,y),2)
                pg.draw.line(layer,(255,244,171,220),(x,y-3),(x,y+3),2)
        screen.blit(layer,(0,0))

    def draw_region_atmosphere(self, screen):
        weights = dict(self.scene_weights())
        if self.quality == 'performance':
            # The panoramas already contain their regional color treatment.
            # Skipping another full-screen alpha pass saves substantial time
            # in browsers without reducing texture or sprite resolution.
            if weights.get(0,0):
                for i in range(8):
                    x = round((i*113+self.time*20)%WIDTH)
                    y = 557+round(math.sin(self.time*2+i)*3)
                    pg.draw.line(screen,(166,227,245),(x,y),(x+22,y),2)
            return
        cave = weights.get(2,0)
        if cave:
            shade = self.atmosphere_layer
            shade.fill((0, 0, 0, 0))
            shade.fill((4,14,35,round(105*cave)))
            center = (round(self.player.centerx-self.camera_x),self.player.centery)
            for radius,alpha in [(220,70),(170,42),(115,15)]:
                pg.draw.ellipse(shade,(4,14,35,round(alpha*cave)),
                                (center[0]-radius,center[1]-radius,radius*2,radius*2))
            screen.blit(shade,(0,0))
        # Apply the local light to the complete playable scene. UI is drawn
        # afterward and therefore keeps its neutral, readable ice palette.
        red = green = blue = alpha = 0.0
        for region, weight in weights.items():
            color, strength = SCENE_GRADES[region]
            red += color[0] * weight
            green += color[1] * weight
            blue += color[2] * weight
            alpha += strength * weight
        grade = self.atmosphere_layer
        grade.fill((round(red), round(green), round(blue), round(alpha)))
        screen.blit(grade, (0, 0))
        if weights.get(0,0):
            for i in range(12):
                x = round((i*79+self.time*20)%WIDTH)
                y = 557+round(math.sin(self.time*2+i)*3)
                pg.draw.line(screen,(166,227,245),(x,y),(x+22,y),2)
    def draw_intro(self, screen):
        self.ui.intro(self, screen)


async def main():
    pg.init()
    window = GameWindow()
    pg.display.set_caption('Antarctic Penguin - Fish Adventure')
    game = Game()
    pg.display.set_icon(game.penguin_right)
    clock = pg.time.Clock()
    running = True
    try:
        while running:
            # Browsers present at 60 Hz. A 50 FPS cap produces uneven 16/32 ms
            # frame pacing on a 60 Hz canvas even when rendering is fast enough.
            target_fps = 60
            dt = min(clock.tick(target_fps) / 1000, 1 / 30)
            jump = False
            for event in pg.event.get():
                if window.handle(event,game):
                    jump = False
                    continue
                if event.type == pg.QUIT:
                    game.ask_exit()
                    jump = False
                elif event.type == pg.KEYDOWN:
                    jump = game.handle_key(event.key) or jump
                    if game.exit_open or game.score_ui.open:
                        jump = False
                elif event.type in (pg.TEXTINPUT,pg.TEXTEDITING) and not game.exit_open:
                    game.score_ui.text_event(event)
                elif event.type == pg.MOUSEBUTTONDOWN and event.button==1:
                    pos = window.game_position(event.pos)
                    if pos is not None:
                        game.handle_click(pos)
            if game.quit_requested:
                running = False
                continue
            keys = pg.key.get_pressed()
            direction = int(keys[pg.K_RIGHT] or keys[pg.K_d]) - int(keys[pg.K_LEFT] or keys[pg.K_a])
            vertical = int(keys[pg.K_DOWN] or keys[pg.K_s])-int(keys[pg.K_UP] or keys[pg.K_w] or keys[pg.K_SPACE])
            jump_held = bool(keys[pg.K_SPACE] or keys[pg.K_UP] or keys[pg.K_w])
            if not window.open:
                game.update(dt, direction, jump,
                            bool(keys[pg.K_DOWN] or keys[pg.K_s]), vertical,
                            jump_held)
            window.present(game)
            # Browser builds must return control to the WebAssembly event loop
            # once per frame. On desktop this simply yields until the next tick.
            await asyncio.sleep(0)
    finally:
        game.save_score()
        pg.quit()


if __name__ == '__main__':
    asyncio.run(main())

