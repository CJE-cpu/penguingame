"""Ice-themed Korean interface, drawn at native resolution."""
import pygame as pg

INK = (28, 64, 87)
MUTED = (70, 111, 135)
ICE = (227, 246, 252)
EDGE = (127, 199, 224)
BLUE = (39, 130, 172)


class IceUI:
    def __init__(self):
        regular = pg.font.match_font('malgungothic,nanumgothic')
        bold = pg.font.match_font('malgungothic,nanumgothic', bold=True)
        self.small = pg.font.Font(regular, 14)
        self.body = pg.font.Font(regular, 18)
        self.heading = pg.font.Font(bold or regular, 24)
        self.title = pg.font.Font(bold or regular, 36)

    def panel(self, screen, rect, dark=False):
        rect = pg.Rect(rect)
        shadow = pg.Surface((rect.width + 8, rect.height + 8), pg.SRCALPHA)
        pg.draw.rect(shadow, (17, 51, 79, 65), (4, 5, rect.width, rect.height), border_radius=15)
        screen.blit(shadow, rect.topleft)
        pg.draw.rect(screen, BLUE if dark else ICE, rect, border_radius=14)
        pg.draw.rect(screen, (171, 226, 244) if dark else EDGE, rect, 2, border_radius=14)
        pg.draw.line(screen, (218, 246, 255) if dark else (255, 255, 255),
                     (rect.left + 16, rect.top + 4), (rect.right - 16, rect.top + 4), 2)

    def text(self, screen, text, pos, font=None, color=INK, center=False):
        image = (font or self.body).render(text, True, color)
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
        region = min(len(regions)-1, game.player.centerx//1200)
        self.text(screen, regions[region][0], (28, 21), self.body)
        self.text(screen, f'탐험 {region+1}/6 · 저장 지점 {game.checkpoint_index+1}', (28, 49), self.small, MUTED)
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
        self.text(screen, '아기 동행 중' if game.carried_baby is not None else '이글루로 돌아가세요', (652, 48), self.small)
        for index, kind in enumerate(k for k,v in game.effects.items() if v > 0):
            x = 12 + index*157
            self.panel(screen, (x, 94, 147, 43))
            self.icon(screen, game.item_images[kind], (x+23, 115), (22, 29))
            name = {'grow':'성장', 'speed':'가속', 'reverse':'반전'}[kind]
            self.text(screen, f'{name} {game.effects[kind]:.1f}초', (x+43, 99), self.small)
            pg.draw.rect(screen, (186, 219, 232), (x+43, 123, 89, 4), border_radius=2)
            pg.draw.rect(screen, BLUE, (x+43, 123, round(89*min(1,game.effects[kind]/8)), 4), border_radius=2)
        self.panel(screen, (12, 565, 565, 27))
        self.text(screen, '← → / A D 이동   SPACE 점프   R 다시 시작   ESC 종료', (25, 569), self.small)
        for i, (_, color) in enumerate(regions):
            pg.draw.rect(screen, color, (598+i*30, 574, 28, 8), border_radius=3)
        marker = 598 + int(game.player.centerx/7200*180)
        pg.draw.circle(screen, BLUE, (marker, 578), 5)
        pg.draw.circle(screen, 'white', (marker, 578), 3)

    def intro(self, game, screen):
        screen.blit(game.scene_backgrounds[0], (0, 0))
        self.veil(screen)
        self.panel(screen, (32, 24, 736, 550))
        self.icon(screen, game.penguin_right, (100, 83), (49, 66))
        self.text(screen, '남극 펭귄의 모험', (146, 43), self.title)
        self.text(screen, '여섯 개의 얼음 지대를 탐험하고 친구들을 집으로 데려오세요.', (147, 98), self.small, MUTED)
        self.panel(screen, (54, 136, 692, 58), dark=True)
        self.text(screen, '물고기 30마리 수집 + 아기 펭귄 3마리 구조', (400, 154), self.body, 'white', center=True)
        self.text(screen, '아기를 만나면 동행 시작! 이글루에 도착하면 구조 완료 · +100점', (400, 177), self.small, (224,248,255), center=True)
        cards = [
            (game.igloo_image, '이글루 체크포인트', '닿으면 저장 · 실패하면 이곳에서 복귀'),
            (game.crab_image, '게를 조심하세요', '위에서 밟으면 +30점 · 옆에서는 피격'),
            (game.item_images['grow'], '성장 물약 · 8초', '몸이 커지고 게 돌파 · 좁은 길 통과'),
            (game.item_images['speed'], '속도 물약 · 8초', '이동 속도 1.6배 · 얼음에서는 관성'),
            (game.item_images['reverse'], '반전 물약 · 8초', '좌우 키가 반대로! 바람에도 주의'),
            (game.chest_image, '동굴과 얼음 발판', '보물 +100점 · 금 간 발판은 곧 붕괴')]
        for index, (image, title, detail) in enumerate(cards):
            x, y = 54+(index%2)*352, 206+(index//2)*77
            self.panel(screen, (x,y,340,66))
            self.icon(screen, image, (x+30,y+32), (38,40))
            self.text(screen, title, (x+60,y+10), self.body)
            self.text(screen, detail, (x+60,y+38), self.small, MUTED)
        self.text(screen, '← → / A D 이동     SPACE / ↑ / W 점프     R 재시작     ESC 종료', (400, 456), self.small, MUTED, center=True)
        self.panel(screen, (149, 483, 502, 49), dark=True)
        self.text(screen, 'ENTER 또는 SPACE로 모험 시작', (400, 507), self.heading, 'white', center=True)
        self.text(screen, '물고기: 주황 10점 · 파랑 25점 · 황금 50점', (400, 552), self.small, MUTED, center=True)

    def finish(self, game, screen):
        self.veil(screen)
        self.panel(screen, (130, 122, 540, 354))
        self.icon(screen, game.igloo_image, (400, 169), (84,60))
        self.text(screen, '모험을 마쳤어요!', (400, 227), self.title, center=True)
        self.text(screen, '모든 물고기를 찾고 친구들을 안전하게 데려왔습니다.', (400, 269), self.body, MUTED, center=True)
        self.text(screen, f'{game.score}점', (400, 315), self.title, BLUE, center=True)
        self.text(screen, f'물고기 {game.total}마리 · 구조 {game.rescued}마리 · 게 처치 {game.defeated}마리', (400, 360), self.small, MUTED, center=True)
        self.panel(screen, (220, 395, 360, 51), dark=True)
        self.text(screen, 'R 키로 새로운 모험 시작', (400, 420), self.body, 'white', center=True)
