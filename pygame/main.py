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
from art import WorldArt, contact_shadow
from window import GameWindow
from cave import CaveExpedition
from records import ScoreRecords, ScoreUI
from progress import AdventureSave
from ending import EndingSequence, ENDING_NAMES
from sound import GameAudio
from boss import SealBoss

WIDTH, HEIGHT = 800, 600
NORMAL_PLAYER_SIZE = (40, 52)
REGION_WIDTH = 1800
MAP_SCALE = REGION_WIDTH / 1200
REGIONS = [('눈 덮인 해안', (109, 192, 226)), ('미끄러운 빙하', (80, 211, 239)),
           ('얼음 동굴', (106, 129, 179)), ('눈보라 고원', (159, 183, 202)),
           ('갈라진 빙붕', (148, 183, 230)), ('펭귄의 보금자리', (132, 206, 183))]
WORLD_WIDTH = REGION_WIDTH * len(REGIONS)
BLEND_DISTANCE = 180
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
    ([(0,550,250), (315,550,230), (610,550,240), (925,550,275)],
     [(65,390,80), (180,460,150), (345,390,150), (510,320,160),
      (700,390,150), (865,460,160), (1060,370,90)]),
    ([(0,550,350), (420,550,780)],
     [(70,375,90), (190,450,200), (395,365,160), (575,280,180),
      (785,365,160), (975,450,180), (1100,360,70)])]
FISH_TYPES = {'orange': ('orange-fish.png', (255, 255, 255), 10),
              'blue': ('blue-fish.png', (255, 255, 255), 25),
              'gold': ('gold-fish.png', (255, 255, 255), 50)}
DATA = Path(__file__).resolve().parent / 'data'
GRAVITY = 1800
MOVE_SPEED = 270
JUMP_SPEED = -650
JUMP_HOLD_TIME = 0.22
JUMP_HOLD_FORCE = 1050
JUMP_RELEASE_SPEED = -390
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
        self.background = load_image('antarctica-background.png', (WIDTH, HEIGHT))
        # One oversized panorama per region; never join non-seamless image edges.
        self.scene_backgrounds = [load_image('scene-' + scene + '.png', (WIDTH + 400, HEIGHT)) for scene in SCENES]
        self.animation = PenguinAnimation(DATA)
        self.penguin_left = self.animation.cycles['idle'][0]
        self.penguin_right = pg.transform.flip(self.penguin_left,True,False)
        self.big_penguin_left = pg.transform.scale(self.penguin_left,(96,84))
        self.big_penguin_right = pg.transform.flip(self.big_penguin_left,True,False)
        self.art = WorldArt(DATA)
        self.ocean_background = load_image('ocean-panorama-v2.png',(1800,HEIGHT))
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
        self.crab_image = self.enemy_images['crab'][0]
        self.igloo_image = load_image('igloo-checkpoint.png', (112, 85), keep_aspect=True)
        self.cave_image = load_image('ice-cave-entrance.png', (180, 135), keep_aspect=True)
        self.chest_image = load_image('golden-treasure-chest.png', (36, 30), keep_aspect=True)
        self.item_images = {kind: load_image(filename + '-potion.png', (30, 36), keep_aspect=True)
                            for kind, filename in [('grow', 'growth'), ('speed', 'speed'),
                                                   ('shield', 'reverse')]}
        self.item_images['shield'].fill((145, 225, 255, 255),
                                        special_flags=pg.BLEND_RGBA_MULT)
        self.platform_images = {kind: load_image(filename + '-platform-tile-v2.png', (160, 30))
                                for kind, filename in [('snow', 'snow'), ('ice', 'smooth-ice'), ('crumble', 'cracked-ice')]}
        # Region variants share silhouettes but receive the local background's
        # color temperature, keeping collision art consistent without making
        # every biome look like the same pasted tile.
        self.platform_images['cave'] = self.platform_images['snow'].copy()
        self.platform_images['cave'].fill((158, 194, 222, 255), special_flags=pg.BLEND_RGBA_MULT)
        self.platform_images['fracture'] = self.platform_images['crumble'].copy()
        self.platform_images['sunset'] = self.platform_images['snow'].copy()
        self.platform_images['sunset'].fill((255, 216, 228, 255), special_flags=pg.BLEND_RGBA_MULT)
        shelf = load_image('antarctic-ice-shelf-tile-v3.png', (360, 120),
                           keep_aspect=True)
        # The painted source has generous transparent canvas above and below
        # the shelf. Keeping that canvas put the collision top in empty space,
        # making characters and props appear to hover above the artwork.
        visible_shelf = shelf.get_bounding_rect(min_alpha=8)
        if visible_shelf.width and visible_shelf.height:
            shelf = shelf.subsurface(visible_shelf).copy()
        shelf = pg.transform.smoothscale(shelf, (360, 120))
        self.shelf_images = {}
        shelf_tints = {
            'snow': (225, 235, 255, 255), 'ice': (185, 235, 255, 255),
            'cave': (145, 185, 215, 255), 'fracture': (190, 190, 240, 255),
            'crumble': (205, 190, 235, 255), 'sunset': (255, 205, 220, 255),
        }
        for kind, tint in shelf_tints.items():
            image = shelf.copy()
            image.fill(tint, special_flags=pg.BLEND_RGBA_MULT)
            if kind == 'sunset':
                # Ice keeps its blue core but catches the same coral light as
                # the home-region background instead of reading as pasted cyan.
                image.fill((30, 9, 4, 0), special_flags=pg.BLEND_RGBA_ADD)
            self.shelf_images[kind] = image
        self.platform_textures = {}
        # Reuse transparent effect buffers instead of allocating two full
        # screen surfaces every rendered frame in the browser build.
        self.weather_layer = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        self.marker_layer = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        self.atmosphere_layer = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
        self.quality_levels = ('performance', 'balanced', 'high')
        # WebAssembly alpha drawing is much slower than native rendering.
        # Performance mode keeps native resolution and sprites intact; it only
        # reduces decorative particles, light rays and procedural texture work.
        self.quality_index = 0 if sys.platform == 'emscripten' else 2
        self.platforms = []
        self.platform_kinds = {}
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
            for rect in grounds + ledges:
                self.platforms.append(rect)
                kind = ('ice' if region in (1, 3) else 'cave' if region == 2
                        else 'fracture' if region == 4 else 'sunset' if region == 5
                        else 'snow')
                if region == 4 and rect in ledges:
                    kind = 'crumble'
                self.platform_kinds[tuple(rect)] = kind
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
                if region == 2 and kind == 'spirit':
                    platform = self.region_ledges[region][index]
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
        self.finish_open = False
        self.game_over = False
        self.ending = None
        self.lives = STARTING_LIVES
        self.time_bonus = 0
        self.time = 0.0
        self.effects = {kind: 0.0 for kind in ITEM_STYLE}
        self.items = []
        # Five spaced pickups; control-changing potions sit on optional upper paths.
        placements = [('grow',0,False,0,120), ('speed',1,True,0,95),
                      ('shield',2,True,-1,105), ('speed',3,True,-1,100),
                      ('grow',4,False,0,120)]
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
        boss_arena = pg.Rect(2*REGION_WIDTH+800, 350, 650, 200)
        self.boss = SealBoss(boss_arena, self.region_grounds[2][0].top,
                             self.boss_images)
        moved = 0
        for _kind, rect in self.fish:
            if rect.colliderect(self.boss.arena):
                rect.centerx = 2*REGION_WIDTH+230+moved*125
                moved += 1
        self.max_score += self.boss.SCORE
        self.max_score += 6*60 + 170 + 200 + 6*40 + 500 + 225
        self.max_score += 300 + 2*(30+50) + TIME_BONUS_MAX # Caverns, guardians and time bonus.
        self.arrange_potions(placements)
        self.life_items = []
        for region, ledge_index in ((2, -1), (4, 2)):
            platform = self.region_ledges[region][ledge_index]
            self.life_items.append(pg.Rect(platform.left+18,
                                           platform.top-38, 32, 38))
        self.separate_enemy_spawns()

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
        self.time_bonus = max(0, TIME_BONUS_MAX-round(self.time*TIME_BONUS_RATE))
        self.score += self.time_bonus
        self.finish_open = True
        self.audio.play('ending')
        self.save_score()

    def continue_collecting(self):
        self.ending_prompt_open = False
        self.ending_prompt_choice = False

    def handle_key(self, key):
        if key == pg.K_m:
            enabled = self.audio.toggle()
            self.content.say('소리 켜짐' if enabled else '소리 꺼짐')
            return False
        if key == pg.K_F6:
            self.quality_index = (self.quality_index + 1) % len(self.quality_levels)
            self.content.say({'performance':'성능 모드', 'balanced':'균형 모드',
                              'high':'고화질 모드'}[self.quality])
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
            if key in (pg.K_RETURN, pg.K_SPACE, pg.K_RIGHT):
                if self.ending.advance():
                    self.ending = None
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
        elif key == pg.K_x and self.boss.active:
            if self.boss.launch_ice(self.player, self.facing_right):
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
            self.exit_open = True
            self.exit_choice = False

    def ask_restart(self):
        if not self.restart_open:
            self.restart_open = True
            self.restart_choice = False

    def confirm_restart(self):
        self.progress.clear()
        self.reset()

    def handle_click(self, pos):
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

    def platform_texture(self, kind, size, ground=False, joins=(False, False)):
        """Build a cached platform by repeating the painted ice-shelf asset."""
        key = (kind, size, ground, joins)
        if key not in self.platform_textures:
            width, height = size
            visual_height = max(height, 72)
            surface = pg.Surface((width, visual_height), pg.SRCALPHA)
            shelf = pg.transform.smoothscale(self.shelf_images[kind],
                                              (360, visual_height))
            for x in range(0, width, shelf.get_width()):
                surface.blit(shelf, (x, 0))
            self.platform_textures[key] = surface
        return self.platform_textures[key]
    def draw_background(self, screen):
        drift = round(400 * max(0, min(1, self.camera_x / (WORLD_WIDTH-WIDTH))))
        for index, (region, weight) in enumerate(self.scene_weights()):
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
                self.quit_requested or self.score_ui.open or self.game_over):
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
        if jump and self.on_ground:
            self.velocity_y = JUMP_SPEED
            self.on_ground = False
            self.jump_hold = JUMP_HOLD_TIME
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
        boss_event = self.boss.update(dt, self.player)
        if boss_event == 'start':
            self.audio.play('checkpoint')
            self.feedback.emit(self.boss.rect.midtop, '거대 바다표범 등장!', (255, 210, 107))
        elif boss_event == 'impact':
            self.audio.play('hit')
            self.feedback.emit(self.boss.rect.midtop, '빙벽 충돌! 지금 공격!', (143, 235, 247))
        elif boss_event in ('ranged_hit', 'ranged_defeat'):
            self.audio.play('defeat')
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
                self.velocity_y = -470
                self.y = float(self.player.y)
                self.on_ground = False
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
        # Descending from above is a stomp; side and upward contact cause damage.
        for enemy in list(self.enemies):
            if not self.player.colliderect(enemy.rect):
                continue
            if enemy.respawn_safe:
                continue
            if self.effects['grow'] or (self.velocity_y > 0 and previous_bottom <= enemy.previous_top + 3):
                self.enemies.remove(enemy)
                self.combat.defeat(enemy, self.enemy_images)
                self.score += enemy.points
                self.audio.play('defeat')
                self.feedback.emit(enemy.rect.midtop, f'{ENEMY_INFO[enemy.kind][0]} 처치 +{enemy.points}', (255,219,132))
                self.defeated += 1
                if not self.effects['grow']:
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
        for kind, rect in self.fish:
            if self.player.colliderect(rect):
                self.score += FISH_TYPES[kind][2]
                self.content.wallet += 1
                self.audio.play('collect')
                self.feedback.emit(rect.center, f'+{FISH_TYPES[kind][2]}', (255,232,151))
            else:
                remaining_fish.append((kind, rect))
        self.fish = remaining_fish
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
        if self.exit_open:
            self.ui.exit_dialog(self,screen)

    @property
    def quality(self):
        return self.quality_levels[self.quality_index]

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
            screen.blit(self.platform_texture(kind, platform.size, ground, joins), rect)
            if kind == 'crumble' and tuple(platform) in self.crumbles:
                progress = min(1, self.crumbles[tuple(platform)][0] / 0.8)
                pg.draw.rect(screen, (245, 92, 125), (rect.x, rect.y-4, int(rect.width*progress), 3))
        self.draw_adventure(screen)
        # Static world props (cages, levers, dive holes and home decorations)
        # belong behind hazards. Drawing them first prevents enemies from being
        # hidden while their collision box can still damage the player.
        self.content.draw_world(self,screen)
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
        self.ui.hud(self, screen, REGIONS)
        if self.boss.active and not self.boss.defeated:
            self.boss.draw_hud(self, screen)
        else:
            self.ui.rescue_guide(self,screen)
            self.ui.transition(self, screen, REGIONS)
            self.content.draw_hud(self,screen)
        if self.region_banner > 0 and not self.boss.active:
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
            snow = self.weather_layer
            snow.fill((0, 0, 0, 0))
            snow_count = {'performance':24, 'balanced':40, 'high':65}[self.quality]
            for i in range(snow_count):
                x = int((i * 137 - self.time * 180) % WIDTH)
                y = int((i * 83 + self.time * 45) % HEIGHT)
                pg.draw.line(snow, (238, 249, 255, round(255*snow_weight)), (x, y), (x - 12, y + 4), 2)
            screen.blit(snow, (0, 0))

    def rescue_target(self):
        if self.carried_baby is not None:
            return ('home',min(self.checkpoints,key=lambda r:abs(r.centerx-self.player.centerx)))
        waiting = [b['rect'] for b in self.babies if not b['rescued']]
        if waiting:
            return ('baby',min(waiting,key=lambda r:abs(r.centerx-self.player.centerx)+abs(r.centery-self.player.centery)))
        return None

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

