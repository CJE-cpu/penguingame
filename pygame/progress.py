"""Atomic checkpoint saves for the long-form adventure."""
from datetime import datetime
from pathlib import Path
import json
import os
import shutil
import tempfile
from storage import atomic_replace


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
            'ending_completed': game.ending_completed,
            'time_bonus': game.time_bonus,
            'fish': [list(self._rect_key(entry)) for entry in game.fish],
            'items': [list(self._rect_key(entry)) for entry in game.items],
            'life_items': [[rect.x, rect.y] for rect in game.life_items],
            'enemies': [enemy.uid for enemy in game.enemies],
            'defeated': game.defeated,
            'hits': game.hits,
            'falls': game.falls,
            'lives': game.lives,
            'visited': sorted(game.visited_checkpoints),
            'region_fish_rewarded': sorted(game.region_fish_rewarded),
            'babies': [baby['rescued'] for baby in game.babies],
            'rescued': game.rescued,
            'caves': [{
                'region': cave.get('region'),
                'found': cave['found'],
                'treasure': cave['treasure'],
                'expedition': {
                    'stones': sorted(cave.get('expedition', {}).get('stones', set())),
                    'lever': cave.get('expedition', {}).get('lever', False),
                    'cleared': cave.get('expedition', {}).get('cleared', False),
                    'defeated': sorted(cave.get('expedition', {}).get('defeated', set())),
                },
            } for cave in game.caves],
            'boss': {
                'defeated': game.boss.defeated,
                'seal_defeated': game.boss.defeated,
                'skua_defeated': game.skua_boss.defeated,
            },
            'content': {
                'wallet': game.content.wallet,
                'upgrades': game.content.upgrades,
                'quests': game.content.quests,
                'journals': [entry['found'] for entry in game.content.journals],
                'crystals': [entry['found'] for entry in game.content.crystals],
                'research': game.content.research_claimed,
                'escape_cleared': game.content.escape_cleared,
                'ocean_fish': [list(self._rect_key(entry)) for entry in game.content.ocean_fish],
                'ocean_beacons': [entry['active'] for entry in game.content.ocean_beacons],
                'ocean_relic': game.content.ocean_relic_found,
                'dive_states': [{
                    'beacons': [entry['active'] for entry in state['beacons']],
                    'relic_found': state['relic_found'],
                } for state in game.content.dive_states],
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
            atomic_replace(temporary, self.path)
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
            saved_lives = data.get('life_items')
            if saved_lives is not None and not isinstance(saved_lives, list):
                raise ValueError('Invalid life item list')
            if saved_lives is not None:
                life_keys = {tuple(value) for value in saved_lives
                             if isinstance(value, list) and len(value) == 2}
                game.life_items = [rect for rect in game.life_items
                                   if (rect.x, rect.y) in life_keys]
            enemy_ids = set(data.get('enemies', []))
            game.enemies = [enemy for enemy in game.enemies if enemy.uid in enemy_ids]
            game.score = max(0, min(game.max_score, int(data.get('score', 0))))
            game.time = max(0.0, min(10_000_000.0, float(data.get('time', 0))))
            game.ending_completed = bool(data.get('ending_completed', False))
            game.time_bonus = max(0, int(data.get('time_bonus', 0)))
            game.run_id = data.get('run_id') if isinstance(data.get('run_id'), str) else game.run_id
            game.defeated = max(0, int(data.get('defeated', 0)))
            game.hits = max(0, int(data.get('hits', 0)))
            game.falls = max(0, int(data.get('falls', 0)))
            game.lives = max(1, min(3, int(data.get('lives', 3))))
            game.checkpoint_index = checkpoint
            game.visited_checkpoints = {i for i in data.get('visited', [])
                                        if type(i) is int and 0 <= i < len(game.checkpoints)} | {checkpoint}
            game.region_fish_rewarded = {
                i for i in data.get('region_fish_rewarded', [])
                if type(i) is int and 0 <= i < len(game.region_grounds)}
            baby_states = data.get('babies', [])
            if len(baby_states) != len(game.babies):
                raise ValueError('Invalid baby state')
            for baby, rescued in zip(game.babies, baby_states):
                baby['rescued'] = bool(rescued)
            game.rescued = sum(baby['rescued'] for baby in game.babies)
            cave_states = data.get('caves', [])
            if not isinstance(cave_states, list) or len(cave_states) > len(game.caves):
                raise ValueError('Invalid cave state')
            if not all(isinstance(saved, dict) for saved in cave_states):
                raise ValueError('Invalid cave state')
            caves_by_region = {cave.get('region'): cave for cave in game.caves}
            if cave_states and all(type(saved.get('region')) is int for saved in cave_states):
                cave_pairs = [(caves_by_region.get(saved['region']), saved)
                              for saved in cave_states]
                if any(cave is None for cave, _saved in cave_pairs):
                    raise ValueError('Invalid cave region')
            elif len(cave_states) == 2 and {2, 4} <= set(caves_by_region):
                # Version-1 saves made before the third cavern stored only an
                # ordered pair for regions 2 and 4. Preserve those exact caves.
                cave_pairs = [(caves_by_region[region], saved)
                              for region, saved in zip((2, 4), cave_states)]
            else:
                cave_pairs = list(zip(game.caves, cave_states))
            for cave, saved in cave_pairs:
                expedition = saved.get('expedition', {})
                if not isinstance(expedition, dict):
                    raise ValueError('Invalid cave expedition')
                cave['found'] = bool(saved.get('found'))
                cave['treasure'] = bool(saved.get('treasure'))
                cave['expedition'] = {
                    'stones': {i for i in expedition.get('stones', []) if i in (0, 1, 2)},
                    'lever': bool(expedition.get('lever')),
                    'cleared': bool(expedition.get('cleared')),
                    'defeated': {i for i in expedition.get('defeated', []) if i in (0, 1)},
                }
            boss_state = data.get('boss', {})
            game.boss.restore_defeated(bool(
                boss_state.get('seal_defeated', boss_state.get('defeated', False))))
            game.skua_boss.restore_defeated(bool(boss_state.get('skua_defeated', False)))
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
            dive_states = content.get('dive_states')
            if (isinstance(dive_states, list)
                    and len(dive_states) == len(game.content.dive_states)):
                for state, saved_state in zip(game.content.dive_states, dive_states):
                    if not isinstance(saved_state, dict):
                        raise ValueError('Invalid dive state')
                    beacon_states = saved_state.get('beacons')
                    if (not isinstance(beacon_states, list)
                            or len(beacon_states) != len(state['beacons'])):
                        raise ValueError('Invalid dive beacon state')
                    for beacon, active in zip(state['beacons'], beacon_states):
                        beacon['active'] = bool(active)
                    state['relic_found'] = bool(saved_state.get('relic_found'))
            else:
                # Older saves had one shared dive record. It belonged to the
                # first entrance; keep that progress without completing dive 2.
                first_state = game.content.dive_states[0]
                beacon_states = content.get('ocean_beacons')
                if (isinstance(beacon_states, list)
                        and len(beacon_states) == len(first_state['beacons'])):
                    for beacon, active in zip(first_state['beacons'], beacon_states):
                        beacon['active'] = bool(active)
                first_state['relic_found'] = bool(content.get('ocean_relic', False))
            game.content.ocean_fish = self._remaining(game.content.ocean_fish,
                                                       content.get('ocean_fish'))
            game.started = True
            # Continuing resumes the saved expedition immediately. Tutorial
            # coaching is an explicit new-game choice and must not reopen here.
            game.coach.enabled = False
            game.coach.modal = None
            game.tutorial = None
            game.spawn = game.checkpoint_spawn(checkpoint)
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
