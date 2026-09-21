"""Ice-themed Korean interface, drawn at native resolution."""
import math
from pathlib import Path
import pygame as pg

INK = (25, 57, 76)
MUTED = (67, 99, 117)
ICE = (235, 247, 248)
EDGE = (161, 206, 215)
BLUE = (36, 101, 127)


class IceUI:
    def __init__(self):
        fonts = Path(__file__).resolve().parent/'data'/'fonts'
        regular = fonts/'GowunDodum-Regular.ttf'
        rounded = fonts/'Jua-Regular.ttf'
        fallback = pg.font.match_font('malgungothic,nanumgothic')
        self.small = pg.font.Font(str(regular) if regular.exists() else fallback,15)
        self.body = pg.font.Font(str(regular) if regular.exists() else fallback,18)
        self.heading = pg.font.Font(str(rounded) if rounded.exists() else fallback,25)
        self.title = pg.font.Font(str(rounded) if rounded.exists() else fallback,38)

    def panel(self, screen, rect, dark=False):
        rect = pg.Rect(rect)
        shadow = pg.Surface((rect.width + 8, rect.height + 8), pg.SRCALPHA)
        pg.draw.rect(shadow, (17, 51, 79, 48), (3, 4, rect.width, rect.height), border_radius=11)
        screen.blit(shadow, rect.topleft)
        pg.draw.rect(screen, BLUE if dark else ICE, rect, border_radius=10)
        pg.draw.rect(screen, (134, 188, 204) if dark else EDGE, rect, 1, border_radius=10)

    def text(self, screen, text, pos, font=None, color=INK, center=False, max_width=None):
        if font in (self.heading,self.title):
            text = text.replace('·',' / ')
        image = (font or self.body).render(text, True, color)
        if max_width and image.get_width()>max_width:
            ratio = max_width/image.get_width()
            image = pg.transform.smoothscale(image,(max_width,max(1,round(image.get_height()*ratio))))
        screen.blit(image, image.get_rect(center=pos) if center else pos)

    def icon(self, screen, image, center, size=(30, 30)):
        ratio = min(size[0]/image.get_width(), size[1]/image.get_height())
        image = pg.transform.scale(image, (max(1, round(image.get_width()*ratio)),
                                          max(1, round(image.get_height()*ratio))))
        screen.blit(image, image.get_rect(center=center))

    def veil(self, screen):
        veil = pg.Surface(screen.get_size(), pg.SRCALPHA)
        veil.fill((13, 41, 68, 145))
        screen.blit(veil, (0, 0))

    def hud(self, game, screen, regions):
        self.panel(screen, (12, 12, 776, 73))
        region = min(len(regions)-1, game.player.centerx//game.region_width)
        self.text(screen, regions[region][0], (28, 21), self.body)
        self.text(screen, f'탐험 {region+1}/6 · 이글루 {game.checkpoint_index+1}', (28, 49), self.small, MUTED)
        for x in (225,370,510,635):
            pg.draw.line(screen,EDGE,(x,29),(x,68))
        self.icon(screen, game.fish_images['gold'], (249, 46))
        self.text(screen, str(game.score), (274, 20), self.heading)
        self.text(screen, '모은 점수', (274, 51), self.small, MUTED)
        self.icon(screen, game.fish_images['blue'], (393, 45))
        self.text(screen, f'{game.total-len(game.fish)}/{game.total}', (417, 20), self.heading)
        self.text(screen, '물고기', (417, 51), self.small, MUTED)
        self.icon(screen, game.baby_image, (532, 46), (24, 32))
        self.text(screen, f'{game.rescued}/3', (553, 20), self.heading)
        self.text(screen, '구조 완료', (553, 51), self.small, MUTED)
        self.text(screen, f'추락 {game.falls} · 피격 {game.hits}', (652, 25), self.small, MUTED)
        self.text(screen, '아기 동행 중' if game.carried_baby is not None else '친구를 찾아보세요', (652, 48), self.small,max_width=122)
        for index, kind in enumerate(k for k,v in game.effects.items() if v > 0):
            x = 12 + index*157
            self.panel(screen, (x, 94, 147, 43))
            self.icon(screen, game.item_images[kind], (x+23, 115), (22, 29))
            name = {'grow':'성장', 'speed':'가속', 'reverse':'반전'}[kind]
            self.text(screen, f'{name} {game.effects[kind]:.1f}초', (x+43, 99), self.small)
            pg.draw.rect(screen, (186, 219, 232), (x+43, 123, 89, 4), border_radius=2)
            pg.draw.rect(screen, BLUE, (x+43, 123, round(89*min(1,game.effects[kind]/8)), 4), border_radius=2)
        self.panel(screen, (12, 565, 565, 27))
        self.text(screen, '← → 이동  SPACE 점프  ↓ 활주  E 행동  TAB 일지  R 재시작', (25, 569), self.small)
        for i, (_, color) in enumerate(regions):
            pg.draw.rect(screen, color, (598+i*30, 574, 28, 8), border_radius=3)
        for index,baby in enumerate(game.babies):
            if baby['rescued'] or index == game.carried_baby:
                continue
            x = 598+round(baby['rect'].centerx/game.world_width*180)
            pg.draw.polygon(screen,(255,219,85),[(x,567),(x-4,573),(x+4,573)])
        marker = 598 + int(game.player.centerx/game.world_width*180)
        pg.draw.circle(screen, BLUE, (marker, 578), 5)
        pg.draw.circle(screen, 'white', (marker, 578), 3)

    def rescue_guide(self,game,screen):
        target = game.rescue_target()
        if target is None or game.won:
            return
        kind,rect = target
        self.panel(screen,(12,147,262,43))
        self.icon(screen,game.baby_image if kind=='baby' else game.igloo_image,(35,168),(27,30))
        dx,dy = rect.centerx-game.player.centerx,rect.centery-game.player.centery
        horizontal = '오른쪽' if dx>40 else '왼쪽' if dx<-40 else '근처'
        vertical = ' 위' if dy<-45 else ' 아래' if dy>45 else ''
        self.text(screen,'친구 위치' if kind=='baby' else '친구와 이글루로', (57,150),self.small)
        self.text(screen,horizontal+vertical,(57,169),self.small,MUTED)
        angle = math.atan2(dy,dx)
        cx,cy = 246,168
        tip = (round(cx+math.cos(angle)*11),round(cy+math.sin(angle)*11))
        left = (round(cx+math.cos(angle+2.5)*8),round(cy+math.sin(angle+2.5)*8))
        right = (round(cx+math.cos(angle-2.5)*8),round(cy+math.sin(angle-2.5)*8))
        pg.draw.polygon(screen,BLUE,[tip,left,right])

    def transition(self, game, screen, regions):
        if game.region_banner <= 0 or game.won:
            return
        elapsed = 2.4-game.region_banner
        opacity = min(1, elapsed/0.3, game.region_banner/0.4)
        card = pg.Surface((298, 54), pg.SRCALPHA)
        self.panel(card, (0, 0, 290, 46), dark=True)
        self.text(card, f'{game.display_region+1}번째 탐험 · {regions[game.display_region][0]}',
                  (145, 23), self.body, 'white', center=True)
        card.set_alpha(round(255*opacity))
        screen.blit(card, (490, 94-round(7*(1-opacity))))

    def intro(self, game, screen):
        screen.blit(game.scene_backgrounds[0], (0, 0))
        self.veil(screen)
        self.panel(screen, (32, 24, 736, 550))
        self.icon(screen, game.penguin_right, (100, 83), (49, 66))
        self.text(screen, '남극 펭귄의 모험', (146, 43), self.title)
        self.text(screen, '남극을 탐험하고 물고기와 친구들을 찾으세요.', (147, 98), self.small, MUTED)
        self.panel(screen, (54, 136, 692, 58), dark=True)
        self.text(screen, '물고기 30마리 + 친구 3마리 구조 + 빙붕 탈출 후 귀환', (400, 154), self.body, 'white', center=True)
        self.text(screen, '친구의 부탁을 해결하면 동행 시작 · 이글루에 데려다 주면 +100점', (400, 177), self.small, (224,248,255), center=True)
        cards = [
            (game.penguin_right, '배로 미끄러지기', '↓ + 이동: 빠른 활주 · 얼음 껍질 돌파'),
            (game.fish_images['blue'], '잠수 탐험 · 산소 35초', '해안 구멍 E · 방향키 수영 · 구멍으로 귀환'),
            (game.baby_image, '친구마다 다른 구조 미션', '얼음 깨기 · 먹이 3마리 · 깃발 레버 E'),
            (game.chest_image, '봉인된 동굴의 보물', '동굴 E · 봉인석 3개 → 레버 → 보물'),
            (game.igloo_image, '친구들과 꾸미는 보금자리', '마지막 이글루 E · 물고기로 둥지와 장식'),
            (game.platform_images['crumble'], '빙붕 탈출과 연구 의뢰', '탈출 32초 · 결정 6개 · TAB 의뢰 확인')]
        for index, (image, title, detail) in enumerate(cards):
            x, y = 54+(index%2)*352, 206+(index//2)*77
            self.panel(screen, (x,y,340,66))
            self.icon(screen, image, (x+30,y+32), (38,40))
            self.text(screen, title, (x+60,y+10), self.body)
            self.text(screen, detail, (x+60,y+38), self.small, MUTED)
        self.text(screen, '← → 이동   SPACE 점프   ↓ 활주   E 행동   TAB 일지   R 재시작   ESC 종료 확인', (400, 456), self.small, MUTED, center=True)
        self.panel(screen, (119, 483, 562, 49), dark=True)
        start_label = 'ENTER 튜토리얼 · N 새 모험'
        if game.progress.available:
            start_label += ' · C 이어하기'
        self.text(screen, start_label, (400, 507), self.heading, 'white', center=True)
        if game.progress.error:
            self.text(screen, game.progress.error, (400, 535), self.small, (194,91,74), center=True)
        self.text(screen, 'F3 점수 기록 · F4 이름 변경(시작 전) · 설명창과 기록 창은 게임 정지', (400, 552), self.small, MUTED, center=True)

    def exit_buttons(self):
        return pg.Rect(188,334,194,54),pg.Rect(418,334,194,54)

    def exit_dialog(self, game, screen):
        self.veil(screen)
        self.panel(screen,(112,169,576,269))
        self.text(screen,'모험을 종료할까요?',(400,215),self.heading,center=True)
        self.text(screen,'점수는 기록되고 최근 체크포인트 진행도 유지됩니다.',(400,265),self.body,MUTED,center=True,max_width=530)
        self.text(screen,'계속하기를 선택하면 그대로 이어서 플레이합니다.',(400,293),self.small,MUTED,center=True)
        for index,(rect,label) in enumerate(zip(self.exit_buttons(),('계속하기','종료'))):
            selected = bool(index)==game.exit_choice
            self.panel(screen,rect,dark=selected)
            self.text(screen,label,rect.center,self.body,'white' if selected else INK,center=True)
        self.text(screen,'← → 선택 · ENTER 확인 · ESC 취소 · 마우스 클릭',(400,412),self.small,MUTED,center=True)

    def finish(self, game, screen):
        self.veil(screen)
        self.panel(screen, (130, 122, 540, 354))
        self.icon(screen, game.igloo_image, (400, 169), (84,60))
        self.text(screen, '모험을 마쳤어요!', (400, 227), self.title, center=True)
        self.text(screen, '물고기와 친구들을 데리고 빙붕을 넘어 돌아왔습니다.', (400, 269), self.body, MUTED, center=True)
        self.text(screen, f'{game.score}점', (400, 315), self.title, BLUE, center=True)
        self.text(screen, f'물고기 {game.total}마리 · 구조 {game.rescued}마리 · 적 처치 {game.defeated}마리', (400, 360), self.small, MUTED, center=True)
        self.text(screen, f'일지 {sum(j["found"] for j in game.content.journals)}/6 · 결정 {sum(c["found"] for c in game.content.crystals)}/6 · 의뢰 {sum(game.content.research_claimed)}/3 · 집 {game.content.upgrades}/3', (400,382),self.small,MUTED,center=True)
        self.panel(screen, (220, 395, 360, 51), dark=True)
        self.text(screen, 'ENTER 계속 · F3 기록 · R 새 모험', (400, 420), self.body, 'white', center=True)
