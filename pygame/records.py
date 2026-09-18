"""Local player profiles and atomic, persistent score records."""
from datetime import datetime
from pathlib import Path
import json
import os
import shutil
import tempfile
import unicodedata
import pygame as pg


def player_name(value):
    if not isinstance(value,str):
        return ''
    return unicodedata.normalize('NFC',''.join(c for c in value if c.isprintable())).strip()[:12]


class ScoreRecords:
    def __init__(self, path=None):
        base = Path(os.environ.get('LOCALAPPDATA') or Path.home()/'.local'/'share')
        self.path = Path(path) if path else base/'AntarcticPenguin'/'scores.json'
        self.name = '탐험가'
        self.best = {}
        self.history = []
        self.error = ''
        self.corrupt = False
        self.load()

    def valid_record(self, entry):
        if not isinstance(entry,dict) or not player_name(entry.get('name')):
            return False
        if not isinstance(entry.get('run'),str) or not isinstance(entry.get('date'),str):
            return False
        for key in ('score','fish','rescued','seconds'):
            value = entry.get(key)
            if type(value) is not int or value<0:
                return False
        return type(entry.get('cleared')) is bool

    def load(self):
        try:
            if not self.path.exists():
                return
            if self.path.stat().st_size>2_000_000:
                raise ValueError('Record file too large')
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data,dict) or data.get('version')!=1:
                raise ValueError('Unsupported record format')
            if not isinstance(data.get('best'),list) or not isinstance(data.get('history'),list):
                raise ValueError('Invalid record lists')
            self.name = player_name(data.get('player_name')) or '탐험가'
            for entry in data['best'][:1000]:
                if self.valid_record(entry):
                    entry = dict(entry,name=player_name(entry['name']))
                    old = self.best.get(entry['name'])
                    if old is None or (entry['score'],entry['cleared'])>(old['score'],old['cleared']):
                        self.best[entry['name']] = entry
            self.history = [dict(e,name=player_name(e['name'])) for e in data['history'][:100] if self.valid_record(e)]
        except (OSError,ValueError,UnicodeError):
            self.corrupt = True
            self.error = '기존 기록을 읽지 못했습니다. 저장 시 원본을 백업합니다.'

    def save(self):
        temporary = None
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            if self.corrupt and self.path.exists():
                backup = self.path.with_name(self.path.name+'.backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
                shutil.copy2(self.path,backup)
                self.corrupt = False
            data = {'version':1,'player_name':self.name,'best':list(self.best.values()),'history':self.history}
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=self.path.parent,
                                             prefix='scores-',suffix='.tmp',delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(data,handle,ensure_ascii=False,indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary,self.path)
            self.error = ''
            return True
        except OSError:
            self.error = '파일 저장 실패 · 현재 기록은 메모리에 유지됩니다.'
            return False
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def set_name(self, name):
        name = player_name(name)
        if not name:
            return False
        self.name = name
        return self.save()

    def record(self, entry):
        if not self.valid_record(entry):
            return False
        entry = dict(entry,name=player_name(entry['name']))
        old = self.best.get(entry['name'])
        if old is None or (entry['score'],entry['cleared'])>=(old['score'],old['cleared']):
            self.best[entry['name']] = entry
        self.history = [entry]+[e for e in self.history if e['run']!=entry['run']]
        self.history = self.history[:100]
        return self.save()

    def ranking(self):
        return sorted(self.best.values(),key=lambda e:(-e['score'],-int(e['cleared']),e['date'],e['name']))


class ScoreUI:
    profile_button = pg.Rect(557,43,182,37)
    rank_button = pg.Rect(556,91,183,30)
    input_rect = pg.Rect(220,270,360,48)
    confirm_button = pg.Rect(280,362,240,43)

    def __init__(self):
        self.mode = None
        self.value = ''
        self.composition = ''
        self.recent = False
        self.page = 0
        self.selected = False

    @property
    def open(self):
        return self.mode is not None

    def close(self):
        if self.mode=='name':
            pg.key.stop_text_input()
        self.mode = None
        self.composition = ''

    def rename(self, game):
        if game.started:
            return
        self.mode = 'name'
        self.value = game.player_name
        self.selected = True
        self.composition = ''
        pg.key.start_text_input()

    def confirm(self, game):
        if player_name(self.value) and not self.composition:
            game.records.set_name(self.value)
            game.player_name = game.records.name
            self.close()

    def key(self, game, key):
        if self.mode=='name':
            if key==pg.K_ESCAPE:
                self.close()
            elif key==pg.K_BACKSPACE and not self.composition:
                self.value = '' if self.selected else self.value[:-1]
                self.selected = False
            elif key==pg.K_a and pg.key.get_mods()&pg.KMOD_CTRL:
                self.selected = True
            elif key==pg.K_RETURN:
                self.confirm(game)
            return True
        if self.mode=='ranking':
            if key in (pg.K_ESCAPE,pg.K_F3):
                self.close()
            elif key==pg.K_TAB:
                self.recent = not self.recent
                self.page = 0
            elif key in (pg.K_LEFT,pg.K_RIGHT):
                entries = game.records.history if self.recent else game.records.ranking()
                self.page = (self.page+(1 if key==pg.K_RIGHT else -1))%max(1,(len(entries)+7)//8)
            return True
        if key==pg.K_F3:
            game.save_score()
            self.mode = 'ranking'
            self.recent,self.page = False,0
            return True
        if key==pg.K_F4 and not game.started:
            self.rename(game)
            return True
        return False

    def text_event(self,event):
        if self.mode!='name':
            return
        if event.type==pg.TEXTINPUT:
            previous = '' if self.selected else self.value
            self.value = unicodedata.normalize('NFC',''.join(c for c in previous+event.text if c.isprintable()))[:12]
            self.selected = False
            self.composition = ''
        elif event.type==pg.TEXTEDITING:
            if self.selected and event.text:
                self.value = ''
                self.selected = False
            self.composition = event.text

    def click(self, game, pos):
        if self.mode=='name':
            if self.confirm_button.collidepoint(pos):
                self.confirm(game)
            return True
        if self.mode=='ranking':
            return True
        if not game.started:
            if self.profile_button.collidepoint(pos):
                self.rename(game)
                return True
            if self.rank_button.collidepoint(pos):
                self.key(game,pg.K_F3)
                return True
        return False

    def draw(self, game, screen):
        ui = game.ui
        if not game.started:
            ui.panel(screen,self.profile_button)
            ui.text(screen,f'{game.player_name} / F4',self.profile_button.center,ui.small,center=True,max_width=166)
            ui.panel(screen,self.rank_button,dark=True)
            ui.text(screen,'F3 점수 기록',self.rank_button.center,ui.small,'white',center=True)
        if not self.open:
            return
        ui.veil(screen)
        if self.mode=='name':
            ui.panel(screen,(160,161,480,277))
            ui.text(screen,'탐험가 이름',(400,203),ui.heading,center=True)
            ui.text(screen,'한글·영문 이름을 12자까지 입력하세요.',(400,245),ui.small,center=True)
            ui.panel(screen,self.input_rect)
            if self.selected:
                pg.draw.rect(screen,(183,220,231),(232,279,min(330,ui.body.size(self.value)[0]+6),28),border_radius=4)
            value = self.value+self.composition+('|' if pg.time.get_ticks()%1000<500 else '')
            ui.text(screen,value,(234,282),ui.body,max_width=333)
            ui.text(screen,'ENTER 저장 · ESC 취소 · BACKSPACE 지우기',(400,339),ui.small,center=True)
            ui.panel(screen,self.confirm_button,dark=True)
            ui.text(screen,'이 이름으로 탐험하기',self.confirm_button.center,ui.body,'white',center=True)
            return
        ui.panel(screen,(62,48,676,504))
        ui.text(screen,'최근 탐험 기록' if self.recent else '탐험가 최고 점수',(400,85),ui.heading,center=True)
        ui.text(screen,f'현재 플레이어: {game.player_name} · 같은 컴퓨터의 기록',(400,120),ui.small,center=True)
        entries = game.records.history if self.recent else game.records.ranking()
        ui.text(screen,'순위 / 이름',(88,156),ui.small)
        ui.text(screen,'점수',(385,156),ui.small)
        ui.text(screen,'결과 / 수집',(470,156),ui.small)
        ui.text(screen,'기록 날짜',(626,156),ui.small)
        for i,entry in enumerate(entries[self.page*8:(self.page+1)*8]):
            y = 183+i*34
            if entry['name']==game.player_name:
                pg.draw.rect(screen,(211,236,240),(80,y-3,640,31),border_radius=6)
            ui.text(screen,f"{self.page*8+i+1:02}  {entry['name']}",(88,y),ui.body,max_width=272)
            ui.text(screen,str(entry['score']),(385,y),ui.body,max_width=75)
            ui.text(screen,'완주' if entry['cleared'] else '미완주',(470,y),ui.small)
            ui.text(screen,f"{entry['fish']}/30 · {entry['rescued']}/3",(527,y),ui.small,max_width=92)
            ui.text(screen,entry['date'][:10],(626,y),ui.small,max_width=88)
        if not entries:
            ui.text(screen,'아직 기록이 없어요. 물고기를 찾아 첫 점수를 남겨보세요!',(400,292),ui.body,center=True)
        ui.text(screen,'TAB 최고/최근 전환 · ← → 페이지 · F3 / ESC 닫기',(400,475),ui.small,center=True)
        ui.text(screen,f'{self.page+1}/{max(1,(len(entries)+7)//8)} · 진행 중인 모험은 기록 창을 여는 동안 정지합니다.',(400,500),ui.small,center=True)
        message = game.records.error or '점수는 자동 저장됩니다. 맵 진행 상황은 저장하지 않습니다.'
        ui.text(screen,message,(400,528),ui.small,center=True,max_width=638)
