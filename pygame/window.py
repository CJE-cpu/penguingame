"""Resizable presentation; game coordinates always remain 800 x 600."""
import pygame as pg


class GameWindow:
    sizes = ((640,480),(800,600),(1024,768),(1280,960))
    button = pg.Rect(704,535,84,25)

    def __init__(self):
        self.screen = pg.display.set_mode((800,600),pg.RESIZABLE)
        self.canvas = pg.Surface((800,600))
        self.open = False
        self.choice = 1

    def viewport(self):
        width,height = self.screen.get_size()
        scale = min(width/800,height/600)
        size = (max(1,round(800*scale)),max(1,round(600*scale)))
        return pg.Rect((width-size[0])//2,(height-size[1])//2,*size)

    def game_position(self, pos):
        rect = self.viewport()
        if not rect.collidepoint(pos):
            return None
        return ((pos[0]-rect.x)*800/rect.w,(pos[1]-rect.y)*600/rect.h)

    def rows(self):
        return [pg.Rect(240,240+i*43,320,36) for i in range(len(self.sizes))]

    def apply(self):
        self.screen = pg.display.set_mode(self.sizes[self.choice],pg.RESIZABLE)
        self.open = False

    def handle(self,event,game):
        if event.type == pg.VIDEORESIZE:
            self.screen = pg.display.get_surface()
            return True
        if event.type == pg.QUIT:
            self.open = False
            return False
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_F2 and not game.exit_open:
                self.open = not self.open
                return True
            if self.open:
                if event.key == pg.K_ESCAPE:
                    self.open = False
                elif event.key in (pg.K_UP,pg.K_DOWN):
                    self.choice = (self.choice+(1 if event.key==pg.K_DOWN else -1))%len(self.sizes)
                elif event.key == pg.K_RETURN:
                    self.apply()
                return True
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.game_position(event.pos)
            if self.open:
                if pos is not None:
                    for index,rect in enumerate(self.rows()):
                        if rect.collidepoint(pos):
                            self.choice = index
                            self.apply()
                            break
                return True
            if pos is not None and self.button.collidepoint(pos) and not game.exit_open:
                self.open = True
                return True
        return False

    def present(self,game):
        game.draw(self.canvas)
        ui = game.ui
        if not game.exit_open:
            ui.panel(self.canvas,self.button,dark=True)
            ui.text(self.canvas,'F2 창 크기',self.button.center,ui.small,'white',center=True)
        if self.open:
            ui.veil(self.canvas)
            ui.panel(self.canvas,(190,155,420,330))
            ui.text(self.canvas,'게임 창 크기',(400,193),ui.heading,center=True)
            for index,(rect,size) in enumerate(zip(self.rows(),self.sizes)):
                selected = index == self.choice
                ui.panel(self.canvas,rect,dark=selected)
                ui.text(self.canvas,f'{size[0]} × {size[1]}',rect.center,ui.body,
                        'white' if selected else (28,64,87),center=True)
            ui.text(self.canvas,'↑↓ 선택 · ENTER 적용 · ESC 닫기',(400,433),ui.small,center=True)
            ui.text(self.canvas,'창 가장자리를 드래그해도 조절할 수 있어요.',(400,461),ui.small,center=True)
        self.screen.fill((10,25,39))
        rect = self.viewport()
        pg.transform.smoothscale(self.canvas,rect.size,self.screen.subsurface(rect))
        pg.display.flip()
