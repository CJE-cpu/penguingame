"""Headless checks: python pygame/test_game.py."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import unittest
import math
import tempfile
from pathlib import Path
import pygame as pg
from main import Game, REGION_WIDTH, WORLD_WIDTH, REGIONS, Enemy, TIME_BONUS_MAX, TIME_BONUS_RATE
from window import GameWindow
from cave import CaveExpedition
from records import ScoreRecords
from unittest.mock import patch


class AdventureChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init()
        cls.screen = pg.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pg.quit()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(temporary.cleanup)
        self.score_path = Path(temporary.name)/'scores.json'
        self.game = Game(score_path=self.score_path)
        self.game.started = True

    def test_resized_window_preserves_ratio_and_mouse_coordinates(self):
        window = GameWindow()
        window.screen = pg.Surface((1200,600))
        self.assertEqual(window.viewport(),pg.Rect(200,0,800,600))
        self.assertIsNone(window.game_position((100,300)))
        self.assertEqual(window.game_position((600,300)),(400,300))
        window.screen = pg.Surface((640,480))
        self.assertEqual(window.game_position((320,240)),(400,300))
        window.open = True
        window.present(self.game)

    def test_window_options_keyboard_and_scaled_click(self):
        window = GameWindow()
        self.assertTrue(window.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_F2),self.game))
        self.assertTrue(window.open)
        window.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_UP),self.game)
        window.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN),self.game)
        self.assertEqual(window.screen.get_size(),(640,480))
        self.assertFalse(window.open)
        window.open = True
        center = window.rows()[1].center
        window.handle(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=(center[0]*0.8,center[1]*0.8)),self.game)
        self.assertEqual(window.screen.get_size(),(800,600))
        window.open = True
        window.handle(pg.event.Event(pg.KEYDOWN,key=pg.K_ESCAPE),self.game)
        self.assertFalse(window.open)
        self.assertFalse(self.game.exit_open)

    def place(self, platform, center, velocity=0, grown=False):
        g = self.game
        g.player.size = (40, 52)
        g.player.midbottom = (round(center), platform.top)
        g.x, g.y = map(float, g.player.topleft)
        g.velocity_x, g.velocity_y = velocity, 0
        g.on_ground = True
        g.surface_kind = g.platform_kinds[tuple(platform)]
        g.effects = {'grow': 100 if grown else 0, 'speed': 0, 'reverse': 0}
        g.crumbles.clear()
        g.won = False

    def test_checkpoint_effect_only_on_first_visit_but_spawn_still_changes(self):
        g = self.game
        for index in (1,2,1,2,0,1):
            g.player.midbottom = g.checkpoints[index].midbottom
            g.update_adventure(0)
            self.assertEqual(g.checkpoint_index,index)
        saves = [b for b in g.feedback.bursts if b['text']=='저장 완료']
        self.assertEqual(len(saves),2)
        self.assertEqual(g.visited_checkpoints,{0,1,2})
        g.respawn()
        g.update_adventure(0)
        self.assertFalse(any(b['text']=='저장 완료' for b in g.feedback.bursts))

    def test_checkpoint_progress_survives_restart_and_revisit_saves_silently(self):
        g = self.game
        collected = g.fish.pop(0)
        g.score = 345
        g.time = 91.5
        g.content.wallet = 4
        g.content.journals[0]['found'] = True
        g.content.crystals[1]['found'] = True
        g.content.quests[0] = True
        g.babies[0]['rescued'] = True
        g.rescued = 1
        g.caves[0]['found'] = True
        g.caves[0]['expedition'] = {
            'stones': {0, 2}, 'lever': False, 'cleared': False, 'defeated': {1}}
        g.player.midbottom = g.checkpoints[2].midbottom
        g.update_adventure(0)
        self.assertTrue(g.progress.available)
        self.assertTrue(any(b['text']=='저장 완료' for b in g.feedback.bursts))

        restored = Game(score_path=self.score_path)
        self.assertTrue(restored.continue_adventure())
        self.assertTrue(restored.started)
        self.assertEqual(restored.checkpoint_index, 2)
        self.assertEqual(restored.player.topleft, restored.spawn)
        self.assertEqual(restored.score, 345)
        self.assertEqual(restored.time, 91.5)
        self.assertEqual(restored.content.wallet, 4)
        self.assertTrue(restored.content.journals[0]['found'])
        self.assertTrue(restored.content.crystals[1]['found'])
        self.assertTrue(restored.babies[0]['rescued'])
        self.assertEqual(restored.caves[0]['expedition']['stones'], {0, 2})
        self.assertFalse(any(kind == collected[0] and rect.x == collected[1].x and
                             rect.y == collected[1].y for kind, rect in restored.fish))

        restored.feedback.reset()
        restored.player.move_ip(200, 0)
        restored.update_adventure(0)
        restored.player.midbottom = restored.checkpoints[2].midbottom
        restored.update_adventure(0)
        self.assertFalse(any(b['text']=='저장 완료' for b in restored.feedback.bursts))

    def test_corrupt_checkpoint_is_backed_up_and_new_adventure_remains_available(self):
        path = self.score_path.with_name('progress.json')
        path.write_text('{broken', encoding='utf-8')
        game = Game(score_path=self.score_path)
        self.assertFalse(game.continue_adventure())
        self.assertFalse(game.started)
        self.assertFalse(path.exists())
        self.assertTrue(list(path.parent.glob('progress.json.backup-*')))
        self.assertIn('새 모험', game.progress.error)

    def test_three_lives_trigger_game_over_and_restart(self):
        g = self.game
        for expected in (2, 1):
            g.respawn(hit=True)
            self.assertEqual(g.lives, expected)
            self.assertFalse(g.game_over)
        g.respawn(hit=False)
        self.assertEqual(g.lives, 0)
        self.assertTrue(g.game_over)
        self.assertEqual(g.hits, 2)
        self.assertEqual(g.falls, 1)
        self.assertFalse(g.progress.available)
        elapsed = g.time
        g.update(2.0, direction=1)
        self.assertEqual(g.time, elapsed)
        g.handle_key(pg.K_RETURN)
        self.assertTrue(g.started)
        self.assertFalse(g.game_over)
        self.assertEqual(g.lives, 3)

    def test_fast_clear_awards_time_bonus_only_once(self):
        g = self.game
        g.fish.clear()
        for baby in g.babies:
            baby['rescued'] = True
        g.rescued = len(g.babies)
        g.content.escape_cleared = True
        g.time = 120
        g.player.midbottom = g.checkpoints[-1].midbottom
        g.x, g.y = map(float, g.player.topleft)
        starting_score = g.score
        g.update(0)
        expected = max(0, TIME_BONUS_MAX-round(120*TIME_BONUS_RATE))
        self.assertTrue(g.won)
        self.assertEqual(g.time_bonus, expected)
        self.assertEqual(g.score, starting_score+expected)
        g.finish_open = False
        g.update(0)
        self.assertEqual(g.score, starting_score+expected)

    def test_ending_sequence_pauses_game_and_returns_to_free_exploration(self):
        g = self.game
        g.won = True
        g.finish_open = True
        g.score = 2600
        g.time = 430
        g.time_bonus = 940
        before = g.time
        g.update(1.0)
        self.assertEqual(g.time, before)
        g.handle_key(pg.K_RETURN)
        self.assertIsNotNone(g.ending)
        frames = []
        for page in range(4):
            g.ending.time = 1.0
            g.draw(self.screen)
            frames.append(pg.image.tobytes(self.screen, 'RGB'))
            self.assertEqual(g.time, before)
            if page < 3:
                g.handle_key(pg.K_RETURN)
                self.assertEqual(g.ending.page, page+1)
        self.assertEqual(len(set(frames)), 4)
        g.handle_key(pg.K_LEFT)
        self.assertEqual(g.ending.page, 2)
        g.handle_key(pg.K_RIGHT)
        self.assertEqual(g.ending.page, 3)
        g.handle_key(pg.K_RETURN)
        self.assertIsNone(g.ending)
        self.assertFalse(g.finish_open)
        self.assertTrue(g.won)

    def test_grounded_objects_use_visible_base_as_floor(self):
        g = self.game
        for image in (g.igloo_image,g.cave_image,g.chest_image,
                      g.art.objects['nest'],g.art.objects['home-flag'],g.art.objects['lever-down']):
            rect = g.art.grounded(self.screen,image,(300,450))
            self.assertEqual(rect.y+g.art.contact_row(image),450)

    def test_cavern_puzzle_persists_and_rewards_only_once(self):
        g = self.game
        for index in range(2):
            g.player.midbottom = g.caves[index]['rect'].midbottom
            g.content.action(g)
            cave = g.cave_expedition
            self.assertIsNotNone(cave)
            cave.enemies = []
            cave.player.midbottom = cave.lever.midbottom
            cave.action(g)
            self.assertFalse(cave.state['lever'])
            for stone in cave.stones:
                cave.player.midbottom = stone.midbottom
                cave.x,cave.y = map(float,cave.player.topleft)
                cave.vy = 0
                g.update(0)
            self.assertEqual(len(cave.state['stones']),3)
            cave.player.midbottom = (80,550)
            cave.action(g)
            self.assertIsNone(g.cave_expedition)
            g.content.action(g)
            cave = g.cave_expedition
            cave.enemies = []
            self.assertEqual(len(cave.state['stones']),3)
            g.content.book_open = True
            position,time = cave.player.copy(),cave.time
            g.update(1,1,True)
            self.assertEqual((cave.player,cave.time),(position,time))
            g.content.book_open = False
            g.ask_exit()
            g.update(1,1,True)
            self.assertEqual(cave.time,time)
            g.handle_key(pg.K_ESCAPE)
            cave.player.midbottom = cave.lever.midbottom
            g.handle_key(pg.K_e)
            self.assertTrue(cave.state['lever'])
            score,wallet = g.score,g.content.wallet
            cave.player.midbottom = cave.chest.midbottom
            cave.action(g)
            cave.action(g)
            self.assertEqual(g.score,score+100)
            self.assertTrue(g.caves[index]['treasure'])
            g.draw(self.screen)
            cave.player.midbottom = cave.exit.midbottom
            cave.action(g)
            self.assertIsNone(g.cave_expedition)
            self.assertEqual(g.score,score+250)
            self.assertEqual(g.content.wallet,wallet+3)
            self.assertEqual(g.player.bottom,min(g.region_ledges[2 if index==0 else 4],key=lambda p:p.y).top)
            cave = CaveExpedition(g,index)
            g.cave_expedition = cave
            cave.player.midbottom = cave.chest.midbottom
            cave.action(g)
            cave.player.midbottom = cave.exit.midbottom
            cave.action(g)
            self.assertEqual(g.score,score+250)

    def test_cavern_gate_and_low_passage_match_collisions(self):
        g = self.game
        cave = CaveExpedition(g,0)
        g.cave_expedition = cave
        cave.enemies = []
        cave.player.midbottom = (cave.arch.left-24,550)
        cave.x,cave.y = map(float,cave.player.topleft)
        for _ in range(10):
            cave.update(g,1/60,1,False,False)
        self.assertEqual(cave.player.right,cave.arch.left)
        for _ in range(30):
            cave.update(g,1/60,1,False,True)
        self.assertGreater(cave.player.left,cave.arch.right)
        cave.player.midbottom = (cave.gate.left-25,550)
        cave.x,cave.y = map(float,cave.player.topleft)
        for frame in range(35):
            cave.update(g,1/60,1,frame==0,False)
        self.assertLessEqual(cave.player.right,cave.gate.left)

    def test_named_scores_reload_sort_and_keep_best_per_player(self):
        g = self.game
        records = g.records
        records.set_name('눈송이')
        base = {'name':'눈송이','run':'first','score':180,'fish':8,'rescued':1,'seconds':90,
                'cleared':False,'date':'2026-09-18T12:00:00'}
        self.assertTrue(records.record(base))
        records.record(dict(base,score=140,run='second'))
        records.record(dict(base,score=200,name='빙하',run='third',cleared=True))
        records.record(dict(base,score=220,run='first',cleared=True))
        loaded = ScoreRecords(self.score_path)
        self.assertEqual(loaded.name,'눈송이')
        self.assertEqual([r['score'] for r in loaded.ranking()],[220,200])
        self.assertEqual(len(loaded.history),3)
        self.assertEqual(sum(e['run']=='first' for e in loaded.history),1)
        self.assertTrue(loaded.best['눈송이']['cleared'])

    def test_score_reset_preserves_history_but_tutorial_does_not_record(self):
        g = self.game
        g.player_name = '얼음별'
        g.score = 125
        run = g.run_id
        g.handle_key(pg.K_r)
        self.assertTrue(g.restart_open)
        self.assertEqual(g.run_id, run)
        g.handle_key(pg.K_RIGHT)
        g.handle_key(pg.K_RETURN)
        self.assertEqual(g.records.best['얼음별']['score'],125)
        self.assertEqual(g.records.history[0]['run'],run)
        self.assertNotEqual(g.run_id,run)
        self.assertEqual(g.score,0)
        g.start(True)
        g.score = 900
        g.reset()
        self.assertEqual(len(g.records.history),1)

    def test_restart_confirmation_defaults_to_cancel_pauses_and_supports_mouse(self):
        g = self.game
        g.score = 80
        run = g.run_id
        position = g.player.copy()
        g.handle_key(pg.K_r)
        self.assertTrue(g.restart_open)
        self.assertFalse(g.restart_choice)
        g.update(2, 1, True)
        self.assertEqual(g.player, position)
        g.handle_key(pg.K_RETURN)
        self.assertFalse(g.restart_open)
        self.assertEqual(g.run_id, run)
        g.handle_key(pg.K_r)
        g.handle_key(pg.K_ESCAPE)
        self.assertFalse(g.restart_open)
        g.handle_key(pg.K_r)
        g.handle_click(g.ui.restart_buttons()[0].center)
        self.assertFalse(g.restart_open)
        g.handle_key(pg.K_r)
        g.handle_click(g.ui.restart_buttons()[1].center)
        self.assertNotEqual(g.run_id, run)
        self.assertEqual(g.score, 0)
        self.assertFalse(g.started)

    def test_score_ui_korean_name_and_pause_preserve_current_game(self):
        g = self.game
        g.started = False
        g.handle_key(pg.K_F4)
        self.assertEqual(g.score_ui.mode,'name')
        g.score_ui.text_event(pg.event.Event(pg.TEXTEDITING,text='눈',start=0,length=1))
        g.handle_key(pg.K_RETURN)
        self.assertTrue(g.score_ui.open)
        g.score_ui.text_event(pg.event.Event(pg.TEXTINPUT,text='눈송이'))
        g.handle_key(pg.K_RETURN)
        self.assertEqual(g.player_name,'눈송이')
        self.assertFalse(g.score_ui.open)
        g.started = True
        g.score = 80
        g.content.diving = True
        position,oxygen,time = g.content.swimmer.copy(),g.content.oxygen,g.time
        g.handle_key(pg.K_F3)
        g.update(1,1,True,True,1)
        self.assertEqual((g.content.swimmer,g.content.oxygen,g.time),(position,oxygen,time))
        g.draw(self.screen)
        g.handle_key(pg.K_TAB)
        self.assertTrue(g.score_ui.recent)
        g.handle_key(pg.K_ESCAPE)
        self.assertFalse(g.exit_open)
        self.assertFalse(g.score_ui.open)
        g.handle_key(pg.K_F4)
        self.assertFalse(g.score_ui.open)
        self.assertEqual(g.records.best['눈송이']['score'],80)

    def test_record_write_failure_keeps_previous_file_and_reports_error(self):
        records = self.game.records
        records.set_name('안전한 기록')
        before = self.score_path.read_bytes()
        with patch('records.os.replace',side_effect=PermissionError('read-only')):
            self.assertFalse(records.set_name('새 이름'))
        self.assertEqual(self.score_path.read_bytes(),before)
        self.assertTrue(records.error)
        self.assertFalse(list(self.score_path.parent.glob('scores-*.tmp')))

    def test_corrupt_records_are_backed_up_and_invalid_entries_ignored(self):
        self.score_path.write_text('{broken',encoding='utf-8')
        records = ScoreRecords(self.score_path)
        self.assertTrue(records.error)
        self.assertTrue(records.set_name('다시 시작'))
        backups = list(self.score_path.parent.glob('scores.json.backup-*'))
        self.assertEqual(len(backups),1)
        self.assertEqual(backups[0].read_text(encoding='utf-8'),'{broken')
        self.assertEqual(ScoreRecords(self.score_path).name,'다시 시작')
        self.assertFalse(records.record({'name':'bad','score':-1}))
        self.assertFalse(records.set_name('  '))

    def test_growth_preserves_passage_and_attacks(self):
        g = self.game
        g.enemies = []
        g.items = []
        g.fish = [('orange', pg.Rect(-1000, 0, 36, 24))]
        paths = []
        for grown in (False, True):
            self.place(g.region_grounds[0][0], 150, grown=grown)
            path = []
            for frame in range(100):
                g.update(1/60, 1, frame in (0, 45))
                path.append(tuple(g.player))
            paths.append(path)
        self.assertEqual(*paths)
        platform = g.region_grounds[0][-1]
        self.place(platform, platform.centerx, grown=True)
        enemy = Enemy(platform, 0)
        g.enemies = [enemy]
        score = g.score
        g.update(1/60)
        self.assertEqual(g.enemies, [])
        self.assertEqual(g.score, score + 30)
        self.assertEqual(g.player.size, (40, 52))

    def test_every_platform_is_reachable(self):
        g = self.game
        g.enemies = []
        g.items = []
        g.babies = []
        g.fish = [('orange', pg.Rect(-1000, 0, 36, 24))]
        for region in range(len(REGIONS)):
            nodes = g.region_grounds[region] + g.region_ledges[region]
            reached = {0}
            while True:
                before = set(reached)
                for dst_index, dst in enumerate(nodes):
                    if dst_index in reached:
                        continue
                    for src_index in list(reached):
                        src = nodes[src_index]
                        if src.top - dst.top > 118:
                            continue
                        gap = max(src.left - dst.right, dst.left - src.right, 0)
                        if gap > 180:
                            continue
                        direction = 1 if dst.centerx >= src.centerx else -1
                        positions = (src.left + 25, src.centerx, src.right - 25,
                                     max(src.left+25, min(src.right-25, dst.centerx)),
                                     max(src.left+25, min(src.right-25, dst.left-70)))
                        success = False
                        for start in positions:
                            for hold in (12, 24, 48):
                                # Each route probe is independent from the three-life run.
                                g.lives, g.game_over = 3, False
                                self.place(src, start, direction*270, grown=True)
                                for tick in range(65):
                                    g.update(1/60, direction if tick < hold else 0, tick == 0)
                                    if (g.on_ground and g.player.bottom == dst.top
                                            and g.player.right > dst.left and g.player.left < dst.right):
                                        reached.add(dst_index)
                                        success = True
                                        break
                                if success:
                                    break
                            if success:
                                break
                        if success:
                            break
                if reached == before:
                    break
            self.assertEqual(len(reached), len(nodes), (region, reached, len(nodes)))

    def test_objectives_and_checkpoint(self):
        g = self.game
        self.assertEqual(g.total, 30)
        self.assertEqual(len(g.babies), 3)
        baby = g.babies[0]
        g.content.quests[0] = True
        g.player.topleft = baby['rect'].topleft
        g.update_adventure(0)
        self.assertEqual(g.carried_baby, 0)
        g.player.midbottom = g.checkpoints[1].midbottom
        g.update_adventure(0)
        self.assertEqual(g.rescued, 1)
        self.assertEqual(g.score, 100)
        g.respawn()
        self.assertEqual(g.player.topleft, g.spawn)
        self.assertEqual(g.score, 100)
        for cave in g.caves:
            g.player.topleft = (cave['rect'].right-45, 498)
            g.update_adventure(0)
            self.assertFalse(cave['treasure'])
        self.assertEqual(g.score, 100)
        g.fish = []
        g.update(1/60)
        self.assertFalse(g.won)
        g.rescued = 3
        g.content.escape_cleared = True
        self.place(g.region_grounds[-1][0],g.checkpoints[-1].centerx)
        g.update(1/60)
        self.assertTrue(g.won)

    def test_scene_rendering(self):
        g = self.game
        g.started = False
        g.draw(self.screen)
        g.started = True
        for region in range(len(REGIONS)):
            self.place(g.region_grounds[region][0], region*REGION_WIDTH+70, grown=True)
            g.camera_x = max(0, min(WORLD_WIDTH-800, g.player.centerx-400))
            g.draw(self.screen)
        for image in [g.penguin_left, g.baby_image, g.crab_image, *g.item_images.values()]:
            self.assertEqual(image.get_at((0, 0)).a, 0)

    def test_growth_pickup_expiry_and_crumble(self):
        g = self.game
        potion = next(rect for kind, rect in g.items if kind == 'grow')
        platform = next(p for p in g.platforms if p.top == potion.bottom and p.contains(pg.Rect(potion.x, p.top, 30, 1)))
        self.place(platform, potion.centerx)
        g.update(1/60)
        self.assertEqual(g.effects['grow'], 8)
        self.assertEqual(g.player.size, (40, 52))
        g.effects['grow'] = 0.01
        g.update(1/60)
        self.assertEqual(g.effects['grow'], 0)
        self.assertEqual(g.player.size, (40, 52))
        platform = g.region_ledges[4][0]
        self.place(platform, platform.centerx)
        g.update(1/60)
        self.assertIn(tuple(platform), g.crumbles)
        g.update_adventure(0.9)
        self.assertNotIn(platform, g.active_platforms())
        g.player.topleft = (55, 498)
        g.update_adventure(4.1)
        self.assertIn(platform, g.active_platforms())

    def test_boundary_blending_and_camera(self):
        g = self.game
        for boundary in range(REGION_WIDTH, WORLD_WIDTH, REGION_WIDTH):
            g.player.centerx = boundary
            weights = g.scene_weights()
            self.assertEqual([weight for _, weight in weights], [0.5, 0.5])
            g.player.centerx = boundary-1
            left = dict(g.scene_weights())
            g.player.centerx = boundary+1
            right = dict(g.scene_weights())
            for region in left:
                self.assertLess(abs(left[region]-right[region]), 0.01)
        g.camera_x = 650
        g.player.centerx = REGION_WIDTH+1
        g.update_presentation(1/60)
        self.assertTrue(650 < g.camera_x < REGION_WIDTH-399)
        self.assertEqual(g.region_banner, 2.4)
        self.assertEqual(g.display_region, 1)
        g.ui.transition(g, self.screen, [('region', (0,0,0))]*6)
        g.update_presentation(1)
        self.assertAlmostEqual(g.region_banner, 1.4)
        g.update_presentation(2)
        self.assertEqual(g.region_banner, 0)
        g.player.centerx = REGION_WIDTH-1
        g.update_presentation(1/60)
        self.assertEqual(g.display_region, 0)
        self.assertEqual(g.region_banner, 2.4)
        g.respawn()
        self.assertEqual(g.region_banner, 0)
        self.assertEqual(g.camera_x, 0)

    def test_penguin_animation_states(self):
        g = self.game
        g.items = []
        g.enemies = []
        self.place(g.region_grounds[0][0], 75)
        g.update(1/60)
        self.assertEqual(g.animation.state, 'idle')
        frames = set()
        for _ in range(64):
            g.animation.update(1/60,g.player,0,True,True,4.5)
            self.assertEqual(g.animation.state, 'walk')
            frames.add(pg.image.tobytes(g.animation.image(False, True), 'RGBA'))
        self.assertEqual(len(frames), 8)
        self.place(g.region_grounds[0][0], 75)
        g.animation.reset()
        states = set()
        for tick in range(60):
            g.update(1/60, 0, tick == 0)
            states.add(g.animation.state)
            if g.animation.state == 'land':
                self.assertTrue(g.animation.puffs)
        self.assertTrue({'jump', 'fall', 'land', 'idle'} <= states)
        g.animation.state = 'jump'
        normal = g.animation.image(False, False)
        right = g.animation.image(False, True)
        self.assertEqual(pg.image.tobytes(pg.transform.flip(normal, True, False), 'RGBA'),
                         pg.image.tobytes(right, 'RGBA'))
        self.assertEqual(normal.get_size(), (64, 56))
        self.assertEqual(g.animation.image(True, False).get_size(), (96, 84))
        self.assertEqual(g.player.size, (40, 52))
        g.respawn()
        self.assertEqual(g.animation.state, 'idle')
        self.assertFalse(g.animation.puffs)

    def test_reverse_pickups_and_feedback(self):
        g = self.game
        self.assertEqual(sum(kind=='reverse' for kind,rect in g.items),1)
        g.enemies = []
        self.place(g.region_grounds[0][0],75)
        rect = g.player.copy()
        g.items = [('reverse',rect.copy()), ('reverse',rect.copy())]
        g.update(1/60)
        self.assertEqual(g.effects['reverse'],8)
        self.assertEqual(g.items,[])
        self.assertTrue(any('갱신' in b['text'] for b in g.feedback.bursts))
        old = g.player.x
        g.update(1/60,1)
        self.assertLess(g.player.x,old)
        g.items = [('reverse',g.player.copy())]
        g.update(1/60)
        old = g.player.x
        g.update(1/60,1)
        self.assertLess(g.player.x,old)
        g.effects['reverse'] = 0.001
        old = g.player.x
        g.update(1/60,1)
        self.assertGreater(g.player.x,old)
        g.feedback.draw(g,self.screen)
        g.feedback.update(2)
        self.assertEqual(g.feedback.bursts,[])

    def test_enemy_behaviors_and_walk_rate(self):
        g = self.game
        self.assertEqual({e.kind for e in g.enemies},{'crab','seal','skua','spirit'})
        platform = pg.Rect(0,550,400,50)
        seal = Enemy(platform,60,'seal')
        seal.cooldown = 0
        player = pg.Rect(260,498,40,52)
        old = seal.x
        seal.update(1/60,player)
        self.assertGreater(seal.warning,0)
        self.assertEqual(seal.x,old)
        for _ in range(34):
            seal.update(1/60,player)
        self.assertGreater(seal.charge,0)
        old = seal.x
        seal.update(1/60,player)
        self.assertGreater(abs(seal.x-old),3)
        skua = Enemy(platform,60,'skua')
        positions = []
        for _ in range(60):
            skua.update(1/60)
            positions.append(skua.rect.y)
            self.assertTrue(skua.left<=skua.rect.left and skua.rect.right<=skua.right)
        self.assertGreater(max(positions)-min(positions),20)
        spirit = Enemy(platform,60,'spirit')
        spirit.cooldown = 0
        spirit.update(1/60)
        self.assertLess(spirit.rect.y,spirit.base_y)
        for _ in range(60):
            spirit.update(1/60)
        self.assertEqual(spirit.rect.y,spirit.base_y)
        g.animation.reset()
        for _ in range(60):
            g.animation.update(1/60,g.player,0,True,True,20)
        self.assertAlmostEqual(g.animation.walk_clock,1.3)

    def test_sparse_potions_and_visible_animation(self):
        g = self.game
        self.assertEqual(len(g.items),5)
        self.assertEqual([sum(k==kind for k,r in g.items) for kind in ('grow','speed','reverse')],[2,2,1])
        for kind,rect in g.items:
            self.assertTrue(any(p.top==rect.bottom and p.left<=rect.left and p.right>=rect.right for p in g.platforms))
            if kind == 'reverse':
                self.assertTrue(any(p.top==rect.bottom for group in g.region_ledges for p in group))
        g.enemies = []
        self.place(g.region_grounds[0][0],75)
        for kind in ('grow','speed','reverse'):
            g.items = [(kind,g.player.copy())]
            g.update(1/60)
            self.assertEqual([k for k,v in g.effects.items() if v>0],[kind])
            self.assertEqual(g.feedback.bursts[-1]['kind'],kind)
        g.effects = {'grow':8,'speed':0,'reverse':0}
        g.feedback.update(0.15,g)
        self.assertTrue(1<g.feedback.size_scale<1.5)
        self.assertGreater(g.feedback.player_image(g).get_height(),56)
        g.effects = {'grow':0,'speed':8,'reverse':0}
        g.velocity_x = 270
        g.feedback.update(0.05,g)
        self.assertTrue(g.feedback.trails)
        g.feedback.draw_aura(g,self.screen)
        g.feedback.draw(g,self.screen)
        self.assertEqual(g.player.size,(40,52))

    def test_potions_leave_reaction_space_from_every_enemy_patrol(self):
        g = self.game
        for kind, item in g.items:
            pickup = pg.Rect(0, 0, 40, 52)
            pickup.midbottom = item.midbottom
            for enemy in g.enemies:
                vertical = 95 if enemy.kind in ('skua', 'spirit') else 38
                patrol = pg.Rect(enemy.left, enemy.base_y-vertical,
                                 enemy.right-enemy.left,
                                 enemy.rect.height+vertical*2)
                self.assertFalse(pickup.inflate(360, 0).colliderect(patrol),
                                 (kind, item, enemy.uid, patrol))

    def test_cave_platforms_use_distinct_layered_textures(self):
        g = self.game
        first = CaveExpedition(g, 0)
        second = CaveExpedition(g, 1)
        blue = first.platform_texture((180, 50))
        violet = second.platform_texture((180, 50))
        fragile = second.platform_texture((180, 50), True)
        self.assertNotEqual(pg.image.tobytes(blue, 'RGB'),
                            pg.image.tobytes(violet, 'RGB'))
        self.assertNotEqual(pg.image.tobytes(violet, 'RGB'),
                            pg.image.tobytes(fragile, 'RGB'))
        self.assertGreater(len(set(pg.image.tobytes(blue, 'RGB'))), 6)

    def test_exit_dialog_pauses_and_preserves_nested_screen(self):
        g = self.game
        g.coach.enabled = True
        g.coach.explain('swim')
        lesson = g.coach.modal
        g.content.diving = True
        g.effects['grow'] = 4
        g.grow_guard = 1
        g.content.escape_active = True
        g.content.escape_left = 20
        g.handle_key(pg.K_ESCAPE)
        self.assertTrue(g.exit_open)
        self.assertFalse(g.exit_choice)
        snapshot = (g.time,g.player.copy(),g.content.oxygen,g.effects.copy(),g.grow_guard,g.content.escape_left)
        g.handle_key(pg.K_r)
        g.update(2,1,True,True,1)
        self.assertEqual(snapshot,(g.time,g.player,g.content.oxygen,g.effects,g.grow_guard,g.content.escape_left))
        g.draw(self.screen)
        g.handle_key(pg.K_ESCAPE)
        self.assertFalse(g.exit_open)
        self.assertEqual(g.coach.modal,lesson)
        self.assertFalse(g.quit_requested)
        g.coach.modal = None
        g.handle_key(pg.K_ESCAPE)
        g.handle_key(pg.K_RETURN)
        self.assertFalse(g.quit_requested)
        self.assertFalse(g.exit_open)
        g.update(1)
        self.assertEqual(g.content.oxygen,snapshot[2]-1)

    def test_exit_confirmation_keys_mouse_and_intro(self):
        g = self.game
        g.reset()
        g.handle_key(pg.K_ESCAPE)
        g.handle_key(pg.K_RETURN)
        self.assertFalse(g.started)
        self.assertFalse(g.quit_requested)
        g.ask_exit()
        g.ask_exit()
        g.handle_click(g.ui.exit_buttons()[0].center)
        self.assertFalse(g.exit_open)
        g.ask_exit()
        g.handle_key(pg.K_RIGHT)
        g.handle_key(pg.K_RETURN)
        self.assertTrue(g.quit_requested)
        g.reset()
        g.ask_exit()
        g.handle_click(g.ui.exit_buttons()[1].center)
        self.assertTrue(g.quit_requested)

    def test_growth_expiration_protects_against_contact(self):
        g = self.game
        enemy = g.enemies[0]
        g.enemies = [enemy]
        g.items = []
        g.player.midbottom = enemy.rect.midbottom
        g.x,g.y = map(float,g.player.topleft)
        g.effects['grow'] = 0.001
        g.update(1/60)
        self.assertEqual(g.effects['grow'],0)
        self.assertEqual(g.grow_guard,1.5)
        self.assertGreaterEqual(g.invincible,1.5)
        self.assertIn(enemy,g.enemies)
        self.assertFalse(g.combat.hurt)
        g.draw(self.screen)
        g.enemies = []
        for _ in range(100):
            g.update(1/60)
        self.assertEqual(g.grow_guard,0)
        self.assertEqual(g.invincible,0)
        g.effects['grow'] = 0.001
        g.invincible = 3
        g.update(1/60)
        self.assertGreater(g.invincible,2.9)

    def test_research_rewards_and_crystal_persistence(self):
        g = self.game
        c = g.content
        self.assertEqual(WORLD_WIDTH,10800)
        for crystal in c.crystals:
            r = crystal['rect']
            self.assertFalse(any(r.colliderect(fish) for kind,fish in g.fish))
            g.player.center = r.center
            c.update(g,0)
        self.assertEqual(c.research_progress()[2],6)
        self.assertEqual(g.score,240)
        c.ocean_fish = c.ocean_fish[3:]
        for j in c.journals[:3]:j['found'] = True
        self.place(g.region_grounds[0][0],g.checkpoints[0].centerx)
        for _ in range(3):c.action(g)
        self.assertEqual(c.research_claimed,[True,True,True])
        self.assertEqual(g.score,740)
        self.assertEqual(c.wallet,10)
        c.action(g)
        self.assertEqual(g.score,740)
        self.assertEqual(c.wallet,10)
        g.respawn()
        self.assertEqual(c.research_progress()[2],6)
        self.assertEqual(c.research_claimed,[True,True,True])
        self.assertEqual(c.wallet,10)
        c.book_open = True
        g.handle_key(pg.K_LEFT)
        self.assertEqual(c.book_page,6)
        g.draw(self.screen)
        g.handle_key(pg.K_RIGHT)
        self.assertEqual(c.book_page,0)
        g.draw(self.screen)
        g.reset()
        self.assertEqual(g.content.wallet,0)
        self.assertFalse(any(g.content.research_claimed))
        self.assertFalse(any(crystal['found'] for crystal in g.content.crystals))

    def test_generated_art_cycles_and_ground_anchors(self):
        g = self.game
        for action in ('slide','swim'):
            frames = g.animation.cycles[action]
            self.assertEqual(len(frames),6)
            self.assertGreaterEqual(len({pg.image.tobytes(f,'RGBA') for f in frames}),4)
            for frame in frames:
                bounds = frame.get_bounding_rect(min_alpha=128)
                self.assertGreater(bounds.width,bounds.height)
                self.assertEqual(frame.get_at((0,0)).a,0)
                if action=='slide':
                    self.assertLessEqual(bounds.height,30)
                    self.assertEqual(bounds.bottom,frame.get_height())
        for name,frames in g.animation.cycles.items():
            if name not in ('slide','swim'):
                for frame in frames:
                    self.assertEqual(frame.get_bounding_rect(min_alpha=128).bottom,56)
        for frames in g.art.babies.values():
            for frame in frames:
                self.assertEqual(frame.get_bounding_rect(min_alpha=128).bottom,40)
        for kind,frames in g.enemy_images.items():
            self.assertEqual(len(frames),4)
            self.assertGreaterEqual(len({pg.image.tobytes(f,'RGBA') for f in frames}),3)
        for kind,frames in g.art.fishes.items():
            self.assertEqual(len(frames),4)
            self.assertGreaterEqual(len({pg.image.tobytes(f,'RGBA') for f in frames}),3)
        self.assertEqual(len(g.art.objects),12)
        self.assertEqual(g.ocean_background.get_size(),(1800,600))
        self.assertEqual(g.ocean_background.get_at((0,0)).a,255)
        body = g.player.copy()
        g.animation.clock = 0.2
        g.draw(self.screen)
        self.assertEqual(g.player,body)

    def test_action_frames_and_paused_instruction_timers(self):
        g = self.game
        for action in ('slide','swim'):
            g.animation.clock = 0
            first = g.animation.action_image(action,True)
            g.animation.clock = 0.23
            second = g.animation.action_image(action,True)
            self.assertNotEqual(pg.image.tobytes(first,'RGBA'),pg.image.tobytes(second,'RGBA'))
            self.assertGreater(first.get_width(),first.get_height())
        g.coach.enabled = True
        g.coach.explain('slide')
        g.effects['speed'] = 5
        g.content.escape_active = True
        g.content.escape_left = 12
        g.content.diving = True
        position,time,oxygen = g.player.copy(),g.time,g.content.oxygen
        enemy = g.enemies[0].rect.copy()
        g.update(2,1,True,True,1)
        self.assertEqual(g.player,position)
        self.assertEqual(g.enemies[0].rect,enemy)
        self.assertEqual(g.time,time)
        self.assertEqual(g.effects['speed'],5)
        self.assertEqual(g.content.escape_left,12)
        self.assertEqual(g.content.oxygen,oxygen)
        g.handle_key(pg.K_e)
        self.assertIsNotNone(g.coach.modal)
        self.assertFalse(g.handle_key(pg.K_SPACE))
        self.assertIsNone(g.coach.modal)
        g.update(1)
        self.assertEqual(g.content.oxygen,oxygen-1)
        self.assertFalse(g.coach.explain('slide'))
        self.assertIsNone(g.coach.modal)

    def test_complete_tutorial_with_real_controls(self):
        g = self.game
        g.reset()
        g.handle_key(pg.K_RETURN)
        t = g.tutorial
        self.assertIsNotNone(t)
        self.assertIsNotNone(g.coach.modal)
        g.handle_key(pg.K_RETURN)
        for _ in range(120):
            g.update(1/60,1)
            if t.step==1:
                break
        self.assertEqual(t.step,1)
        g.handle_key(pg.K_RETURN)
        for frame in range(120):
            g.update(1/60,1,frame==0)
            if t.step==2:
                break
        self.assertEqual(t.step,2)
        g.handle_key(pg.K_RETURN)
        for _ in range(180):
            g.update(1/60,1,slide=True)
            if t.step==3:
                break
        self.assertEqual(t.step,3)
        g.handle_key(pg.K_RETURN)
        for _ in range(60):
            g.update(1/60,1)
            if abs(t.player.centerx-t.baby.centerx)<50:
                break
        g.handle_key(pg.K_e)
        self.assertTrue(t.carrying)
        for _ in range(100):
            g.update(1/60,1)
            if t.step==4:
                break
        self.assertEqual(t.step,4)
        g.handle_key(pg.K_RETURN)
        g.handle_key(pg.K_TAB)
        self.assertTrue(g.content.book_open)
        g.draw(self.screen)
        g.handle_key(pg.K_TAB)
        self.assertEqual(t.step,5)
        g.handle_key(pg.K_RETURN)
        for _ in range(150):
            g.update(1/60,1)
            if abs(t.player.centerx-t.hole.centerx)<40:
                break
        g.handle_key(pg.K_e)
        self.assertTrue(t.diving)
        for _ in range(200):
            dx,dy = 470-t.swimmer.x,350-t.swimmer.y
            g.update(1/60,0 if abs(dx)<3 else (1 if dx>0 else -1),swim_vertical=0 if abs(dy)<3 else (1 if dy>0 else -1))
            if t.swim_fish:
                break
        self.assertTrue(t.swim_fish)
        g.draw(self.screen)
        for _ in range(200):
            dx,dy = 100-t.swimmer.x,170-t.swimmer.y
            g.update(1/60,0 if abs(dx)<3 else (1 if dx>0 else -1),swim_vertical=0 if abs(dy)<3 else (1 if dy>0 else -1))
            if t.swimmer.distance_to((100,170))<60:
                break
        g.handle_key(pg.K_e)
        self.assertTrue(t.finished)
        g.handle_key(pg.K_RETURN)
        self.assertIsNone(g.tutorial)
        self.assertTrue(g.started)
        self.assertEqual(g.score,0)
        self.assertEqual(g.content.wallet,0)
        self.assertFalse(any(j['found'] for j in g.content.journals))
        self.assertEqual(g.player.topleft,(55,498))

    def test_intro_offers_keyboard_and_mouse_tutorial_skip(self):
        g = self.game
        g.reset()
        choices = g.ui.intro_buttons(g)
        self.assertEqual([action for action, _rect, _label in choices],
                         ['tutorial', 'skip'])
        self.assertIn('튜토리얼 보지 않기', choices[1][2])
        g.handle_click(choices[1][1].center)
        self.assertTrue(g.started)
        self.assertIsNone(g.tutorial)
        self.assertIsNotNone(g.coach.modal)
        g.reset()
        g.handle_key(pg.K_n)
        self.assertTrue(g.started)
        self.assertIsNone(g.tutorial)

    def test_rescue_quests_sliding_and_feed(self):
        g = self.game
        g.enemies = []
        g.items = []
        baby = g.babies[0]
        g.player.midbottom = baby['rect'].midbottom
        g.x,g.y = map(float,g.player.topleft)
        g.update_adventure(0)
        self.assertIsNone(g.carried_baby)
        g.on_ground = True
        feet = g.player.bottom
        g.update(1/60,1,slide=True)
        self.assertTrue(g.content.quests[0])
        self.assertEqual(g.carried_baby,0)
        self.assertEqual(g.player.height,28)
        self.assertEqual(g.player.bottom,feet)
        g.update(1/60)
        self.assertEqual(g.player.height,52)
        g.carried_baby = None
        g.player.midbottom = g.babies[1]['rect'].midbottom
        g.content.wallet = 2
        g.content.action(g)
        self.assertFalse(g.content.quests[1])
        g.content.wallet = 3
        g.content.action(g)
        self.assertTrue(g.content.quests[1])
        self.assertEqual(g.content.wallet,0)
        g.update_adventure(0)
        self.assertEqual(g.carried_baby,1)
        g.carried_baby = None
        g.player.midbottom = g.content.lever.midbottom
        g.content.action(g)
        self.assertTrue(g.content.quests[2])
        g.player.midbottom = g.babies[2]['rect'].midbottom
        g.update_adventure(0)
        self.assertEqual(g.carried_baby,2)

    def test_ocean_exit_oxygen_and_bonus_persistence(self):
        g = self.game
        c = g.content
        self.place(g.region_grounds[0][1],c.hole.centerx)
        shore = g.player.midbottom
        c.action(g)
        self.assertTrue(c.diving)
        self.assertEqual(c.oxygen,35)
        c.swimmer.update(c.ocean_fish[0][1].center)
        g.update(1/60,1,swim_vertical=1)
        self.assertEqual(len(c.ocean_fish),5)
        self.assertEqual(c.wallet,1)
        self.assertEqual(g.total,30)
        g.draw(self.screen)
        c.action(g)
        self.assertTrue(c.diving)
        c.swimmer.update(100,115)
        c.action(g)
        self.assertFalse(c.diving)
        self.assertEqual(g.player.midbottom,shore)
        c.action(g)
        self.assertTrue(c.diving)
        c.oxygen = 0.01
        g.update(0.02)
        self.assertFalse(c.diving)
        self.assertEqual(g.falls,1)
        self.assertEqual(c.wallet,1)
        self.assertEqual(len(c.ocean_fish),5)

    def test_swimming_pose_turns_smoothly_and_slows_when_idle(self):
        animation = self.game.animation
        animation.update_swim(0.01,pg.Vector2(1,-1),True)
        self.assertTrue(0<animation.swim_angle<30)
        for _ in range(60):
            animation.update_swim(1/60,pg.Vector2(1,-1),True)
        self.assertAlmostEqual(animation.swim_angle,30,places=2)
        self.assertGreater(animation.swim_image(True).get_height(),42)
        before = animation.swim_clock
        animation.update_swim(1,pg.Vector2(),True)
        self.assertAlmostEqual(animation.swim_clock-before,0.35)
        self.assertLess(abs(animation.swim_angle),0.01)
        animation.update_swim(0.2,pg.Vector2(-1,-1),False)
        self.assertLess(animation.swim_angle,0)

    def test_ocean_collection_effect_and_visible_swimming_bounds(self):
        g = self.game
        c = g.content
        c.diving = True
        c.swimmer.update(c.ocean_fish[0][1].center)
        g.update(1/60)
        self.assertEqual(len(c.ocean_rings),1)
        c.swimmer.update(100,590)
        g.update(0.1)
        self.assertEqual(c.swimmer.y,500)
        c.swimmer.update(100,80)
        g.update(0.1)
        self.assertEqual(c.swimmer.y,125)
        c.draw_ocean(g,self.screen)
        g.update(0.7)
        self.assertFalse(c.ocean_rings)

    def test_journals_shortcut_home_and_escape(self):
        g = self.game
        c = g.content
        journal = c.journals[2]
        g.player.center = journal['rect'].center
        c.update(g,0)
        score = g.score
        c.update(g,0)
        self.assertEqual(score,60)
        self.assertEqual(g.score,score)
        c.book_open = True
        time = g.time
        g.update(1,1)
        self.assertEqual(g.time,time)
        g.draw(self.screen)
        c.book_open = False
        g.player.midbottom = g.caves[0]['rect'].midbottom
        c.action(g)
        self.assertIsNotNone(g.cave_expedition)
        g.cave_expedition.action(g)
        self.assertIsNone(g.cave_expedition)
        self.place(g.region_grounds[5][0],g.checkpoints[-1].centerx)
        c.wallet = 23
        for i in range(3):
            c.action(g)
            self.assertEqual(c.upgrades,i+1)
        self.assertEqual(c.wallet,0)
        c.action(g)
        self.assertEqual(c.upgrades,3)
        g.rescued = 3
        g.fish = []
        g.update(1/60)
        self.assertFalse(g.won)
        c.action(g)
        self.assertTrue(c.escape_active)
        c.escape_left = 0.01
        c.update(g,0.02)
        self.assertFalse(c.escape_cleared)
        self.assertFalse(c.escape_active)
        g.player.centerx = c.escape_start+55
        c.update(g,0)
        self.assertTrue(c.escape_active)
        g.player.centerx = c.escape_end+10
        c.update(g,1)
        self.assertTrue(c.escape_cleared)
        score = g.score
        c.update(g,1)
        self.assertEqual(g.score,score)
        self.place(g.region_grounds[5][0],g.checkpoints[-1].centerx)
        g.update(1/60)
        self.assertTrue(g.won)
        self.assertTrue(g.finish_open)
        g.finish_open = False
        old_x = g.player.x
        g.update(1/60,1)
        self.assertGreater(g.player.x,old_x)
        g.draw(self.screen)

    def test_combat_animation_and_delayed_respawn(self):
        g = self.game
        enemy = g.enemies[0]
        g.effects['grow'] = 8
        g.player.center = enemy.rect.center
        g.x, g.y = map(float, g.player.topleft)
        g.update(1/60)
        self.assertNotIn(enemy,g.enemies)
        self.assertTrue(g.combat.defeated)
        self.assertGreater(g.combat.kick,0)
        g.combat.draw(g,self.screen)
        g.combat.update(1)
        self.assertFalse(g.combat.defeated)
        g.effects['grow'] = 0
        enemy = g.enemies[0]
        g.player.center = enemy.rect.center
        g.x, g.y = map(float,g.player.topleft)
        g.velocity_y = 0
        g.update(1/60)
        self.assertGreater(g.combat.hurt,0)
        hit_pos = g.player.topleft
        g.update(0.1,1,True)
        self.assertEqual(g.player.topleft,hit_pos)
        self.assertEqual(g.hits,0)
        g.draw(self.screen)
        g.update(0.4)
        self.assertEqual(g.hits,1)
        self.assertEqual(g.player.topleft,g.spawn)
        self.assertFalse(g.combat.hurt)

    def test_companion_route_and_building_grounding(self):
        g = self.game
        for checkpoint in g.checkpoints:
            self.assertTrue(any(p.top==checkpoint.bottom and p.left<=checkpoint.left and p.right>=checkpoint.right for p in g.grounds))
        for cave in g.caves:
            r = cave['rect']
            self.assertTrue(any(p.top==r.bottom and p.left<=r.left and p.right>=r.right for p in g.grounds))
        g.carried_baby = 0
        g.player.midbottom = (55,550)
        g.on_ground = True
        g.babies[0]['rect'].midbottom = g.player.midbottom
        g.companion.start(g,g.babies[0])
        recorded = set()
        followed = set()
        for frame in range(100):
            g.time += 1/60
            x = 55+min(frame,70)*4
            y = round(550-math.sin(min(frame,70)/70*math.pi)*90)
            g.player.midbottom = (x,y)
            g.on_ground = frame in (0,70) or frame>70
            recorded.add(g.player.midbottom)
            g.companion.update(g,1/60)
            followed.add(tuple(g.companion.pos))
            if g.companion.airborne:
                self.assertIn(tuple(g.companion.pos),recorded)
            g.companion.draw(g,self.screen)
        self.assertGreater(len(followed),20)
        self.assertGreaterEqual(math.dist(g.companion.pos,g.player.midbottom),36)
        self.assertFalse(g.companion.airborne)
        self.assertEqual(g.companion.pos[1],550)
        g.respawn()
        self.assertIsNone(g.companion.pos)
        self.assertFalse(g.companion.route)

    def test_clear_potions_panorama_and_shaking(self):
        g = self.game
        for kind, rect in g.items:
            self.assertFalse(any(rect.inflate(28,18).colliderect(o) for o in g.potion_obstacles()))
        for camera in (0, 1, 2000, 3999, WORLD_WIDTH-800):
            g.camera_x = camera
            g.player.centerx = 500
            self.screen.fill((255,0,255))
            g.draw_background(self.screen)
            drift = round(400*camera/(WORLD_WIDTH-800))
            expected = g.scene_backgrounds[0].subsurface((drift,0,800,600))
            self.assertTrue(pg.image.tobytes(self.screen,'RGB') == pg.image.tobytes(expected,'RGB'))
        platform = g.region_ledges[4][0]
        original = platform.copy()
        g.camera_x = platform.x-200
        still = g.platform_draw_rect(platform)
        positions = set()
        for elapsed in (0.1,0.2,0.3,0.4,0.5,0.6,0.7):
            g.crumbles[tuple(platform)] = (elapsed,0)
            positions.add(g.platform_draw_rect(platform).topleft)
        self.assertGreater(len(positions),3)
        self.assertEqual(platform,original)
        self.assertIn(platform,g.active_platforms())
        g.crumbles[tuple(platform)] = (0.8,4)
        self.assertNotIn(platform,g.active_platforms())

    def test_baby_markers_and_direction_target(self):
        g = self.game
        baby = g.babies[0]
        g.player.center = baby['rect'].center
        self.assertEqual(g.rescue_target(),('baby',baby['rect']))
        g.camera_x = baby['rect'].centerx-400
        self.screen.fill((0,0,0))
        g.time = 0
        g.draw_baby_markers(self.screen)
        first = pg.image.tobytes(self.screen,'RGB')
        self.screen.fill((0,0,0))
        g.time = 0.6
        g.draw_baby_markers(self.screen)
        self.assertTrue(first != pg.image.tobytes(self.screen,'RGB'))
        g.carried_baby = 0
        self.assertEqual(g.rescue_target()[0],'home')
        g.ui.rescue_guide(g,self.screen)
        g.carried_baby = None
        for baby in g.babies:
            baby['rescued'] = True
        self.assertIsNone(g.rescue_target())


if __name__ == '__main__':
    unittest.main()
