"""Antarctic penguin platformer. Arrows/A/D: move; Space: jump; R: restart."""
from pathlib import Path
from datetime import datetime
from uuid import uuid4
import math
import pygame as pg
from ui import IceUI
from animation import PenguinAnimation
from enemies import Enemy, ENEMY_INFO
from feedback import InteractionEffects
from motion import CombatMotion, BabyCompanion
from adventure import AdventureContent
from tutorial import Coach, TutorialStage
from art import WorldArt
from window import GameWindow
from cave import CaveExpedition
from records import ScoreRecords, ScoreUI
from progress import AdventureSave
from ending import EndingSequence, ENDING_NAMES

WIDTH, HEIGHT = 800, 600
REGION_WIDTH = 1800
MAP_SCALE = REGION_WIDTH / 1200
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
GROW_EXIT_INVINCIBILITY = 1.5
STARTING_LIVES = 3
TIME_BONUS_MAX = 1800
TIME_BONUS_RATE = 2
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
        self.font = self.ui.body
        self.big_font = self.ui.title
        self.intro_font = self.ui.body
        self.intro_title_font = self.ui.title
        self.baby_image = self.art.baby('idle',0)
        self.enemy_images = self.art.enemies
        self.crab_image = self.enemy_images['crab'][0]
        self.igloo_image = load_image('igloo-checkpoint.png', (112, 85), keep_aspect=True)
        self.cave_image = load_image('ice-cave-entrance.png', (180, 135), keep_aspect=True)
        self.chest_image = load_image('golden-treasure-chest.png', (36, 30), keep_aspect=True)
        self.item_images = {kind: load_image(filename + '-potion.png', (30, 36), keep_aspect=True)
                            for kind, filename in [('grow', 'growth'), ('speed', 'speed'), ('reverse', 'reverse')]}
        self.platform_images = {kind: load_image(filename + '-platform-tile.png', (80, 30))
                                for kind, filename in [('snow', 'snow'), ('ice', 'smooth-ice'), ('crumble', 'cracked-ice')]}
        self.platform_textures = {}
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
                kind = 'ice' if region in (1, 3) else 'snow'
                if region == 4 and rect in ledges:
                    kind = 'crumble'
                self.platform_kinds[tuple(rect)] = kind
        self.ground_keys = {tuple(p) for p in self.grounds}
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
        self.home_prompt_dismissed = False
        self.quit_requested = False
        self.coach = Coach()
        self.tutorial = None
        self.cave_expedition = None
        self.animation.reset()
        self.feedback.reset()
        self.combat.reset()
        self.companion.reset()
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
                      ('reverse',2,True,-1,105), ('speed',3,True,-1,100),
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
        self.max_score += 6*60 + 170 + 200 + 6*40 + 500
        self.max_score += 300 + 2*(30+50) + TIME_BONUS_MAX # Caverns, guardians and time bonus.
        self.arrange_potions(placements)

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

    def confirm_ending(self):
        self.ending_prompt_open = False
        self.won = True
        self.ending_type = self.ending_result()
        self.time_bonus = max(0, TIME_BONUS_MAX-round(self.time*TIME_BONUS_RATE))
        self.score += self.time_bonus
        self.finish_open = True
        self.save_score()

    def continue_collecting(self):
        self.ending_prompt_open = False
        self.ending_prompt_choice = False
        self.home_prompt_dismissed = True

    def handle_key(self, key):
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
            self.content.action(self)
        elif key == pg.K_RETURN and self.won:
            self.finish_open = False
            self.ending = EndingSequence(self.ending_type)
        elif self.content.book_open and key in (pg.K_LEFT,pg.K_RIGHT,pg.K_a,pg.K_d):
            self.content.book_page = (self.content.book_page+(1 if key in (pg.K_RIGHT,pg.K_d) else -1))%7
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
        return self.records.record({'run':self.run_id,'name':self.player_name,'score':self.score,
                                    'fish':self.total-len(self.fish),'rescued':self.rescued,
                                    'seconds':round(self.time),'cleared':self.won,
                                    'ending':self.ending_type,
                                    'date':datetime.now().isoformat(timespec='seconds')})

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

    def platform_texture(self, kind, size):
        key = (kind, size)
        if key not in self.platform_textures:
            tile = self.platform_images[kind]
            width, height = size
            surface = pg.Surface(size, pg.SRCALPHA)
            # Repeat only the interior. Rounded corners belong to the two ends.
            middle = tile.subsurface((10, 0, 60, 27))
            body = tile.subsurface((10, 17, 60, 10))
            surface.set_clip((8, 0, width-16, height))
            for y in range(0, height, 10):
                for x in range(8, width-8, 60):
                    surface.blit(body, (x, y))
            for x in range(8, width-8, 60):
                surface.blit(middle, (x, 0))
            surface.set_clip(None)
            surface.blit(tile, (0, 0), (0, 0, 8, 30))
            surface.blit(tile, (width-8, 0), (72, 0, 8, 30))
            border = (13, 49, 89)
            if height > 30:
                pg.draw.line(surface, border, (1, 27), (1, height-2), 3)
                pg.draw.line(surface, border, (width-2, 27), (width-2, height-2), 3)
            pg.draw.line(surface, border, (5, height-2), (width-6, height-2), 2)
            self.platform_textures[key] = surface
        return self.platform_textures[key]

    def draw_background(self, screen):
        drift = round(400 * max(0, min(1, self.camera_x / (WORLD_WIDTH-WIDTH))))
        for index, (region, weight) in enumerate(self.scene_weights()):
            background = self.scene_backgrounds[region]
            if index:
                background = background.copy()
                background.set_alpha(round(255*weight))
            screen.blit(background, (-drift, 0))

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
                self.checkpoint_index = index
                self.spawn = (checkpoint.x + 25, checkpoint.bottom-self.player.height)
                if self.carried_baby is not None:
                    self.babies[self.carried_baby]['rescued'] = True
                    self.carried_baby = None
                    self.companion.reset()
                    self.rescued += 1
                    self.score += 100
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

    def respawn(self, hit=False):
        if not self.consume_life(hit):
            return
        self.animation.reset()
        self.feedback.reset()
        self.combat.reset()
        self.companion.reset()
        self.effects = {kind: 0.0 for kind in ITEM_STYLE}
        self.player.size = (40, 52)
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
        self.invincible = 2.0
        self.grow_guard = 0.0
        self.feedback.emit(self.player.midtop, '피격! 저장 지점 복귀' if hit else '저장 지점에서 다시!', (205,235,255))
        self.camera_x = max(0, min(WORLD_WIDTH - WIDTH, self.player.centerx - WIDTH // 2))
        self.display_region = self.player.centerx // REGION_WIDTH
        self.region_banner = 0.0

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

    def update(self, dt, direction=0, jump=False, slide=False, swim_vertical=0):
        if (self.exit_open or self.restart_open or self.ending_prompt_open or
                self.quit_requested or self.score_ui.open or self.game_over):
            return
        if not self.started:
            return
        if self.coach.modal:
            return
        if self.ending:
            self.ending.update(dt)
            return
        if self.tutorial:
            self.tutorial.update(self,dt,direction,jump,slide,swim_vertical)
            return
        if self.content.book_open:
            return
        if self.cave_expedition:
            self.cave_expedition.update(self,dt,direction,jump,slide)
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
        if self.effects['reverse']:
            direction = -direction
        speed = MOVE_SPEED * (1.6 if self.effects['speed'] else 1.0) * (1.35 if self.content.sliding else 1)
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
                self.combat.defeat(enemy, self.enemy_images)
                self.score += enemy.points
                self.feedback.emit(enemy.rect.midtop, f'{ENEMY_INFO[enemy.kind][0]} 처치 +{enemy.points}', (255,219,132))
                self.defeated += 1
                if not self.effects['grow']:
                    self.player.bottom = enemy.rect.top
                    self.y = float(self.player.y)
                    self.velocity_y = -420
                    self.on_ground = False
            elif not self.invincible:
                self.combat.hit(self.player, enemy)
                self.feedback.emit(self.player.midtop, '피격!', (255,153,153))
                return
        remaining_fish = []
        for kind, rect in self.fish:
            if self.player.colliderect(rect):
                self.score += FISH_TYPES[kind][2]
                self.content.wallet += 1
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
                for other in self.effects:
                    self.effects[other] = 0.0
                self.effects[kind] = ITEM_DURATION
                name = {'grow':'성장! 적 돌파', 'speed':'가속! 속도 증가', 'reverse':'주의! 좌우 반전'}[kind]
                if repeated:
                    name = {'grow':'성장', 'speed':'가속', 'reverse':'반전'}[kind]+' 시간 갱신'
                self.feedback.emit(rect.center, name, ITEM_STYLE[kind][0],kind=kind)
        self.items = remaining_items
        self.content.update(self,dt)
        self.update_adventure(0)
        near_home = self.content.nearby(self,self.checkpoints[-1])
        if not near_home:
            self.home_prompt_dismissed = False
        elif not self.won and not self.home_prompt_dismissed:
            self.ending_prompt_open = True
            self.ending_prompt_choice = False
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
        for platform in self.active_platforms():
            rect = self.platform_draw_rect(platform)
            kind = self.platform_kinds[tuple(platform)]
            screen.blit(self.platform_texture(kind, platform.size), rect)
            if kind == 'crumble' and tuple(platform) in self.crumbles:
                progress = min(1, self.crumbles[tuple(platform)][0] / 0.8)
                pg.draw.rect(screen, (245, 92, 125), (rect.x, rect.y-4, int(rect.width*progress), 3))
        self.draw_adventure(screen)
        for index, (kind, fish) in enumerate(self.fish):
            bob = round(math.sin(self.time * 4 + index) * 3)
            screen.blit(self.art.fish(kind,self.time+index*0.17), fish.move(-self.camera_x, bob))
        for enemy in self.enemies:
            enemy.draw(screen, self.camera_x, self.enemy_images)
        for kind, rect in self.items:
            rect = rect.move(-self.camera_x, 0)
            bob = round(math.sin(self.time*3+rect.x*0.01)*3)
            color = ITEM_STYLE[kind][0]
            pg.draw.ellipse(screen, color, (rect.x+2,rect.bottom-3,26,5),2)
            screen.blit(self.item_images[kind], rect.move(0,bob))
        self.content.draw_world(self,screen)
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
        self.ui.rescue_guide(self,screen)
        self.ui.transition(self, screen, REGIONS)
        self.content.draw_hud(self,screen)
        if self.region_banner > 0:
            label = self.ui.small.render(REGION_HINTS[self.display_region],True,(28,64,87))
            self.ui.panel(screen,(490,149,298,31))
            screen.blit(label,(499,154))
        if self.won and self.finish_open:
            self.ui.finish(self, screen)
        if self.content.book_open:
            self.content.draw_book(self,screen)
        self.coach.draw(self,screen)

    def draw_adventure(self, screen):
        region = min(len(REGIONS) - 1, self.player.centerx // REGION_WIDTH)
        for cave in self.caves:
            rect = cave['rect'].move(-self.camera_x, 0)
            self.art.grounded(screen,self.cave_image,rect.midbottom)
        for index, checkpoint in enumerate(self.checkpoints):
            rect = checkpoint.move(-self.camera_x, 0)
            if index == len(self.checkpoints)-1:
                pg.draw.ellipse(screen,(151,222,190),rect.inflate(70,12),2)
            self.art.grounded(screen,self.igloo_image,rect.midbottom)
            if index == self.checkpoint_index:
                pg.draw.circle(screen, (111, 255, 151), (rect.centerx, rect.top-32), 5)
        for index, baby in enumerate(self.babies):
            if not baby['rescued'] and index != self.carried_baby:
                rect = baby['rect'].move(-self.camera_x, 0)
                image = self.art.baby('idle',self.time+index*0.3)
                screen.blit(image,image.get_rect(midbottom=rect.midbottom))
        snow_weight = dict(self.scene_weights()).get(3, 0)
        if snow_weight > 0:
            snow = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
            for i in range(65):
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
        layer = pg.Surface((WIDTH,HEIGHT),pg.SRCALPHA)
        for index,baby in enumerate(self.babies):
            if baby['rescued'] or index == self.carried_baby:
                continue
            rect = baby['rect'].move(-self.camera_x,0)
            if rect.right<0 or rect.left>WIDTH:
                continue
            cx = rect.centerx
            pulse = (math.sin(self.time*3+index)+1)/2
            for row in range(80):
                pg.draw.line(layer,(255,225,114,round((1-row/80)*45)),
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
    window = GameWindow()
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
            if not window.open:
                game.update(dt, direction, jump, bool(keys[pg.K_DOWN] or keys[pg.K_s]),vertical)
            window.present(game)
    finally:
        game.save_score()
        pg.quit()


if __name__ == '__main__':
    main()

