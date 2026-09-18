"""Visible pickup bursts, floating labels and temporary item auras."""
import math
import pygame as pg


class InteractionEffects:
    def __init__(self):
        self.bursts = []

    def reset(self):
        self.bursts.clear()

    def emit(self, pos, text, color):
        self.bursts.append({'pos':tuple(pos), 'text':text, 'color':color, 'life':1.2})

    def update(self, dt):
        for burst in self.bursts:
            burst['life'] -= dt
        self.bursts = [burst for burst in self.bursts if burst['life']>0]

    def draw(self, game, screen):
        layer = pg.Surface(screen.get_size(), pg.SRCALPHA)
        for burst in self.bursts:
            age = 1.2-burst['life']
            x,y = burst['pos'];x -= game.camera_x
            alpha = round(255*min(1,burst['life']/0.4))
            if age<0.55:
                radius = round(10+age*70)
                pg.draw.circle(layer,(*burst['color'],round(alpha*(1-age/0.55))), (round(x),round(y)), radius, 2)
                for index in range(12):
                    angle = index*math.tau/12
                    px,py = round(x+math.cos(angle)*radius),round(y+math.sin(angle)*radius)
                    pg.draw.circle(layer,(*burst['color'],alpha),(px,py),2)
            label = game.ui.body.render(burst['text'],True,(24,63,84))
            card = pg.Surface((label.get_width()+18,30),pg.SRCALPHA)
            pg.draw.rect(card,(*burst['color'],235),card.get_rect(),border_radius=8)
            card.blit(label,(9,3));card.set_alpha(alpha)
            layer.blit(card,(round(x-card.get_width()/2),round(y-42-age*28)))
        screen.blit(layer,(0,0))

    def draw_aura(self, game, screen):
        active = [k for k,v in game.effects.items() if v>0]
        if not active:
            return
        colors = {'grow':(130,238,152), 'speed':(255,224,111), 'reverse':(214,163,255)}
        layer = pg.Surface(screen.get_size(),pg.SRCALPHA)
        cx = round(game.player.centerx-game.camera_x)
        cy = game.player.centery
        for index,kind in enumerate(active):
            radius = 28+index*5+round(math.sin(game.time*4)*2)
            pg.draw.circle(layer,(*colors[kind],100),(cx,cy),radius,2)
        if game.effects['speed']:
            direction = -1 if game.facing_right else 1
            for i in range(3):
                x = cx+direction*(25+i*7)
                pg.draw.line(layer,(255,228,134,150),(x,cy-8+i*7),(x+direction*14,cy-8+i*7),2)
        screen.blit(layer,(0,0))
