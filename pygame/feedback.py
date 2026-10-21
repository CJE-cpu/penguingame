"""Visible pickup bursts, floating labels and temporary item auras."""
import math
import pygame as pg


class InteractionEffects:
    MAX_BURSTS = 8
    MAX_TRAILS = 4

    def __init__(self):
        self.bursts = []
        self.trails = []
        self.trail_clock = 0.0
        self.size_scale = 1.0
        self.layer = pg.Surface((800, 600), pg.SRCALPHA)
        self.player_scale_cache = {}
        self.label_cache = {}
        self.icon_cache = {}

    def reset(self):
        self.bursts.clear()
        self.trails.clear()
        self.trail_clock = 0.0
        self.size_scale = 1.0

    def emit(self, pos, text, color, kind=None):
        self.bursts.append({'pos':tuple(pos), 'text':text, 'color':color, 'life':1.2, 'kind':kind})
        # A chain pickup or boss hit can emit several reactions in one frame.
        # Keep the newest reactions without letting draw cost grow unbounded.
        if len(self.bursts) > self.MAX_BURSTS:
            del self.bursts[:-self.MAX_BURSTS]

    def update(self, dt, game=None):
        for burst in self.bursts:
            burst['life'] -= dt
        self.bursts = [burst for burst in self.bursts if burst['life']>0]
        self.trails = [(pos,life-dt) for pos,life in self.trails if life>dt]
        if game is not None:
            target = 1.5 if game.effects['grow'] else 1.0
            self.size_scale += (target-self.size_scale)*(1-math.exp(-11*dt))
            self.trail_clock += dt
            interval = 0.12 if getattr(game, 'quality', 'high') == 'performance' else 0.08
            if game.effects['speed'] and abs(game.velocity_x)>20 and self.trail_clock>=interval:
                self.trails.append((game.player.midbottom,0.26))
                self.trails = self.trails[-self.MAX_TRAILS:]
                self.trail_clock %= interval

    def player_image(self, game):
        image = (game.animation.action_image('slide',game.facing_right) if game.content.sliding
                 else game.animation.image(False,game.facing_right))
        # Quantizing the smooth growth keeps the animation fluid while avoiding
        # a new scaled Surface for nearly every frame of the transition.
        scale = round(self.size_scale * 16) / 16
        size = (round(image.get_width()*scale),
                round(image.get_height()*scale))
        if size == image.get_size():
            return image
        key = (id(image), size)
        scaled = self.player_scale_cache.get(key)
        if scaled is None:
            scaled = pg.transform.scale(image, size)
            self.player_scale_cache[key] = scaled
            if len(self.player_scale_cache) > 128:
                self.player_scale_cache.clear()
        return scaled

    @staticmethod
    def _alpha_step(alpha):
        return max(0, min(7, round(alpha / 36)))

    def _label(self, game, text, alpha):
        step = self._alpha_step(alpha)
        key = (text, step)
        label = self.label_cache.get(key)
        if label is None:
            label = game.ui.small.render(text, True, (255,246,198))
            label.set_alpha(step * 36)
            self.label_cache[key] = label
            if len(self.label_cache) > 96:
                self.label_cache.clear()
        return label

    def _icon(self, game, kind, age, alpha):
        scale_step = min(5, round(age * 6))
        alpha_step = self._alpha_step(alpha)
        key = (kind, scale_step, alpha_step)
        icon = self.icon_cache.get(key)
        if icon is None:
            source = game.item_images[kind]
            scale = 1 + scale_step / 12
            size = (round(source.get_width()*scale), round(source.get_height()*scale))
            icon = pg.transform.scale(source, size)
            icon.set_alpha(alpha_step * 36)
            self.icon_cache[key] = icon
        return icon

    def _burst_image(self, game, age, alpha):
        size_step = max(0, min(7, round(age*9)))
        alpha_step = self._alpha_step(alpha)
        key = ('painted-burst', size_step, alpha_step)
        image = self.icon_cache.get(key)
        if image is None:
            source = game.art.environment['pickup-burst']
            size = 30+size_step*11
            image = pg.transform.smoothscale(source, (size, size))
            image.set_alpha(alpha_step*36)
            self.icon_cache[key] = image
        return image

    def draw(self, game, screen):
        if not self.bursts:
            return
        layer = self.layer
        layer.fill((0, 0, 0, 0))
        for burst in self.bursts:
            age = 1.2-burst['life']
            x,y = burst['pos'];x -= game.camera_x
            if x < -120 or x > 920 or y < -120 or y > 720:
                continue
            alpha = round(255*min(1,burst['life']/0.4))
            if age<0.8:
                painted = self._burst_image(game, age, alpha)
                layer.blit(painted, painted.get_rect(center=(round(x),round(y))))
            if burst['kind'] in ('grow','speed','shield'):
                icon = self._icon(game, burst['kind'], age, alpha)
                layer.blit(icon,icon.get_rect(center=(round(x),round(y-25-age*35))))
            else:
                # Scores are secondary to the visible particle burst.
                label = self._label(game, burst['text'], alpha)
                layer.blit(label,(round(x-label.get_width()/2),round(y-36-age*24)))
        screen.blit(layer,(0,0))

    def draw_aura(self, game, screen):
        active = [k for k,v in game.effects.items() if v>0]
        if not self.trails and not active and game.grow_guard <= 0:
            return
        colors = {'grow':(130,238,152), 'speed':(255,224,111), 'shield':(123,211,255)}
        layer = self.layer
        layer.fill((0, 0, 0, 0))
        for pos, life in self.trails:
            alpha = round(150*life/0.26)
            x = round(pos[0]-game.camera_x)
            y = pos[1]-18
            direction = -1 if game.facing_right else 1
            length = 18+round(22*(1-life/0.26))
            pg.draw.line(layer, (255,226,125,alpha), (x,y),
                         (x+direction*length,y), 3)
            pg.draw.line(layer, (207,244,255,alpha//2), (x,y+10),
                         (x+direction*(length-5),y+10), 2)
        cx = round(game.player.centerx-game.camera_x)
        cy = game.player.centery
        if game.grow_guard>0:
            radius = 36+round(math.sin(game.time*8)*2)
            pg.draw.ellipse(layer,(128,224,255,190),(cx-radius,cy-37,radius*2,74),3)
            pg.draw.ellipse(layer,(221,253,255,110),(cx-radius-4,cy-41,radius*2+8,82),2)
        for index,kind in enumerate(active):
            radius = 28+index*5+round(math.sin(game.time*4)*2)
            if kind == 'grow':
                pg.draw.ellipse(layer,(*colors[kind],150),(cx-radius,game.player.bottom-8,radius*2,14),3)
                for i in range(8):
                    phase = (game.time*0.7+i/8)%1
                    angle = i*math.tau/8+game.time*2
                    x = round(cx+math.cos(angle)*(21+phase*10))
                    y = round(game.player.bottom-phase*85)
                    pg.draw.circle(layer,(*colors[kind],round(220*(1-phase))),(x,y),3)
            elif kind == 'shield':
                pulse = math.sin(game.time*5)*2
                rx, ry = radius+7+pulse, radius+14+pulse
                barrier = []
                for point in range(10):
                    angle = -math.pi/2 + point*math.tau/10
                    barrier.append((round(cx+math.cos(angle)*rx),
                                    round(cy+math.sin(angle)*ry)))
                pg.draw.polygon(layer,(*colors[kind],32),barrier)
                pg.draw.polygon(layer,(184,241,255,205),barrier,3)
                inner = [(round(cx+(x-cx)*0.88),round(cy+(y-cy)*0.88))
                         for x,y in barrier]
                pg.draw.lines(layer,(76,177,237,125),True,inner,2)
                # Upper-left facets make the barrier read as curved ice glass.
                pg.draw.line(layer,(244,254,255,210),barrier[8],barrier[9],3)
                pg.draw.line(layer,(225,250,255,170),barrier[9],barrier[0],2)
                for shard in range(5):
                    angle = game.time*1.7+shard*math.tau/5
                    orbit_x = cx+math.cos(angle)*(rx+7)
                    orbit_y = cy+math.sin(angle)*(ry+4)
                    size = 3 if shard%2 else 4
                    points = [(round(orbit_x),round(orbit_y-size)),
                              (round(orbit_x+size),round(orbit_y)),
                              (round(orbit_x),round(orbit_y+size)),
                              (round(orbit_x-size),round(orbit_y))]
                    pg.draw.polygon(layer,(211,249,255,225),points)
                    pg.draw.line(layer,(93,192,239,210),points[1],points[2],1)
        if game.effects['speed']:
            direction = -1 if game.facing_right else 1
            for i in range(3):
                phase = (game.time*3+i/3)%1
                x = round(cx+direction*(20+phase*40))
                y = cy-15+i*13
                pg.draw.lines(layer,(255,228,134,round(220*(1-phase))),False,
                              [(x,y),(x+direction*8,y-4),(x+direction*4,y+3),(x+direction*15,y)],3)
        screen.blit(layer,(0,0))
