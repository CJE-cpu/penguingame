"""Headless checks: python pygame/test_game.py."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import unittest
import math
import pygame as pg
from main import Game, REGION_WIDTH, REGIONS, Enemy


class AdventureChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init()
        cls.screen = pg.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pg.quit()

    def setUp(self):
        self.game = Game()
        self.game.started = True

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
            self.assertTrue(cave['treasure'])
        self.assertEqual(g.score, 300)
        g.fish = []
        g.update(1/60)
        self.assertFalse(g.won)
        g.rescued = 3
        g.update(1/60)
        self.assertTrue(g.won)

    def test_scene_rendering(self):
        g = self.game
        g.started = False
        g.draw(self.screen)
        g.started = True
        for region in range(len(REGIONS)):
            self.place(g.region_grounds[region][0], region*REGION_WIDTH+70, grown=True)
            g.camera_x = max(0, min(6400, g.player.centerx-400))
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
        for boundary in range(1200, 7200, 1200):
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
        g.player.centerx = 1201
        g.update_presentation(1/60)
        self.assertTrue(650 < g.camera_x < 801)
        self.assertEqual(g.region_banner, 2.4)
        self.assertEqual(g.display_region, 1)
        g.ui.transition(g, self.screen, [('region', (0,0,0))]*6)
        g.update_presentation(1)
        self.assertAlmostEqual(g.region_banner, 1.4)
        g.update_presentation(2)
        self.assertEqual(g.region_banner, 0)
        g.player.centerx = 1199
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
        for camera in (0, 1, 2000, 3999, 6400):
            g.camera_x = camera
            g.player.centerx = 500
            self.screen.fill((255,0,255))
            g.draw_background(self.screen)
            drift = round(400*camera/6400)
            expected = g.scene_backgrounds[0].subsurface((drift,0,800,600))
            self.assertEqual(pg.image.tobytes(self.screen,'RGB'), pg.image.tobytes(expected,'RGB'))
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
        g.camera_x = 1200
        self.screen.fill((0,0,0))
        g.time = 0
        g.draw_baby_markers(self.screen)
        first = pg.image.tobytes(self.screen,'RGB')
        self.screen.fill((0,0,0))
        g.time = 0.6
        g.draw_baby_markers(self.screen)
        self.assertNotEqual(first,pg.image.tobytes(self.screen,'RGB'))
        g.carried_baby = 0
        self.assertEqual(g.rescue_target()[0],'home')
        g.ui.rescue_guide(g,self.screen)
        g.carried_baby = None
        for baby in g.babies:
            baby['rescued'] = True
        self.assertIsNone(g.rescue_target())


if __name__ == '__main__':
    unittest.main()
