"""Headless checks: python pygame/test_game.py."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import unittest
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
        platform = g.region_grounds[0][0]
        self.place(platform, 135)
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


if __name__ == '__main__':
    unittest.main()
