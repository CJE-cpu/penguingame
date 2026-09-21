"""Atomic checkpoint saves for the long-form adventure."""
from datetime import datetime
from pathlib import Path
import json
import os
import shutil
import tempfile


class AdventureSave:
    def __init__(self, path=None):
        base = Path(os.environ.get('LOCALAPPDATA') or Path.home()/'.local'/'share')
        self.path = Path(path) if path else base/'AntarcticPenguin'/'progress.json'
        self.error = ''

    @property
    def available(self):
        return self.path.exists()

    def clear(self):
        try:
            self.path.unlink(missing_ok=True)
            self.error = ''
            return True
        except OSError:
            self.error = '진행 저장 파일을 삭제하지 못했습니다.'
            return False

    @staticmethod
    def _rect_key(entry):
        return entry[0], entry[1].x, entry[1].y

    def snapshot(self, game):
        return {
            'version': 1,
            'saved_at': datetime.now().isoformat(timespec='seconds'),
            'run_id': game.run_id,
            'checkpoint': game.checkpoint_index,
            'score': game.score,
            'time': round(game.time, 3),
            'fish': [list(self._rect_key(entry)) for entry in game.fish],
            'items': [list(self._rect_key(entry)) for entry in game.items],
            'enemies': [enemy.uid for enemy in game.enemies],
            'defeated': game.defeated,
            'hits': game.hits,
            'falls': game.falls,
            'visited': sorted(game.visited_checkpoints),
            'babies': [baby['rescued'] for baby in game.babies],
            'rescued': game.rescued,
            'caves': [{
                'found': cave['found'],
                'treasure': cave['treasure'],
                'expedition': {
                    'stones': sorted(cave.get('expedition', {}).get('stones', set())),
                    'lever': cave.get('expedition', {}).get('lever', False),
                    'cleared': cave.get('expedition', {}).get('cleared', False),
                    'defeated': sorted(cave.get('expedition', {}).get('defeated', set())),
                },
            } for cave in game.caves],
            'content': {
                'wallet': game.content.wallet,
                'upgrades': game.content.upgrades,
                'quests': game.content.quests,
                'journals': [entry['found'] for entry in game.content.journals],
                'crystals': [entry['found'] for entry in game.content.crystals],
                'research': game.content.research_claimed,
                'escape_cleared': game.content.escape_cleared,
                'ocean_fish': [list(self._rect_key(entry)) for entry in game.content.ocean_fish],
            },
        }

    def save(self, game):
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            data = self.snapshot(game)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix='progress-', suffix='.tmp', delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            self.error = ''
            return True
        except OSError:
            self.error = '체크포인트 저장에 실패했습니다. 현재 모험은 계속할 수 있습니다.'
            return False
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def _read(self):
        if not self.path.exists() or self.path.stat().st_size > 1_000_000:
            return None
        data = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('version') != 1:
            raise ValueError('Unsupported progress format')
        return data

    @staticmethod
    def _remaining(entries, saved):
        if not isinstance(saved, list):
            raise ValueError('Invalid object list')
        keys = {tuple(value) for value in saved if isinstance(value, list) and len(value) == 3}
        return [entry for entry in entries if AdventureSave._rect_key(entry) in keys]

    def load_into(self, game):
        try:
            data = self._read()
            if data is None:
                return False
            checkpoint = data.get('checkpoint')
            if type(checkpoint) is not int or not 0 <= checkpoint < len(game.checkpoints):
                raise ValueError('Invalid checkpoint')
            content = data.get('content')
            if not isinstance(content, dict):
                raise ValueError('Invalid content')
            game.fish = self._remaining(game.fish, data.get('fish'))
            game.items = self._remaining(game.items, data.get('items'))
            enemy_ids = set(data.get('enemies', []))
            game.enemies = [enemy for enemy in game.enemies if enemy.uid in enemy_ids]
            game.score = max(0, min(game.max_score, int(data.get('score', 0))))
            game.time = max(0.0, min(10_000_000.0, float(data.get('time', 0))))
            game.run_id = data.get('run_id') if isinstance(data.get('run_id'), str) else game.run_id
            game.defeated = max(0, int(data.get('defeated', 0)))
            game.hits = max(0, int(data.get('hits', 0)))
            game.falls = max(0, int(data.get('falls', 0)))
            game.checkpoint_index = checkpoint
            game.visited_checkpoints = {i for i in data.get('visited', [])
                                        if type(i) is int and 0 <= i < len(game.checkpoints)} | {checkpoint}
            baby_states = data.get('babies', [])
            if len(baby_states) != len(game.babies):
                raise ValueError('Invalid baby state')
            for baby, rescued in zip(game.babies, baby_states):
                baby['rescued'] = bool(rescued)
            game.rescued = sum(baby['rescued'] for baby in game.babies)
            cave_states = data.get('caves', [])
            if len(cave_states) != len(game.caves):
                raise ValueError('Invalid cave state')
            for cave, saved in zip(game.caves, cave_states):
                expedition = saved.get('expedition', {})
                cave['found'] = bool(saved.get('found'))
                cave['treasure'] = bool(saved.get('treasure'))
                cave['expedition'] = {
                    'stones': {i for i in expedition.get('stones', []) if i in (0, 1, 2)},
                    'lever': bool(expedition.get('lever')),
                    'cleared': bool(expedition.get('cleared')),
                    'defeated': {i for i in expedition.get('defeated', []) if i in (0, 1)},
                }
            game.content.wallet = max(0, min(1000, int(content.get('wallet', 0))))
            game.content.upgrades = max(0, min(3, int(content.get('upgrades', 0))))
            for name, target in [('quests', game.content.quests),
                                 ('journals', game.content.journals),
                                 ('crystals', game.content.crystals),
                                 ('research', game.content.research_claimed)]:
                values = content.get(name, [])
                if len(values) != len(target):
                    raise ValueError(f'Invalid {name} state')
                if name in ('journals', 'crystals'):
                    for entry, value in zip(target, values):
                        entry['found'] = bool(value)
                else:
                    target[:] = [bool(value) for value in values]
            game.content.escape_cleared = bool(content.get('escape_cleared'))
            game.content.ocean_fish = self._remaining(game.content.ocean_fish,
                                                       content.get('ocean_fish'))
            game.started = True
            game.coach.enabled = True
            game.tutorial = None
            game.spawn = (game.checkpoints[checkpoint].x + 25,
                          game.checkpoints[checkpoint].bottom - game.player.height)
            game.player.topleft = game.spawn
            game.x, game.y = map(float, game.player.topleft)
            game.camera_x = max(0, min(game.world_width - 800, game.player.centerx - 400))
            game.display_region = game.player.centerx // game.region_width
            game.region_banner = 2.4
            game.invincible = 2.0
            game._checkpoint_contact = checkpoint
            self.error = ''
            return True
        except (OSError, ValueError, TypeError, UnicodeError, json.JSONDecodeError):
            try:
                if self.path.exists():
                    backup = self.path.with_name(
                        self.path.name + '.backup-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
                    shutil.move(self.path, backup)
            except OSError:
                pass
            self.error = '진행 저장을 읽지 못해 새 모험으로 시작합니다.'
            return False
