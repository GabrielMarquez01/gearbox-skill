"""Pruebas locales sin red, instalación ni credenciales.

GEARBOX_TEST_REPO permite contrastar otro árbol con las mismas pruebas.
Los fixtures se conservan en tests/.runs (o GEARBOX_TEST_TMP) para inspección.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

REPO = Path(os.environ.get('GEARBOX_TEST_REPO', Path(__file__).resolve().parents[1])).resolve()
RUNS = Path(os.environ.get('GEARBOX_TEST_TMP', Path(__file__).parent / '.runs')).resolve()
RUNS.mkdir(parents=True, exist_ok=True)


class Regression(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='case-', dir=RUNS))
        self.gb = self.root / '.claude/gearbox'
        self.gb.mkdir(parents=True)
        self.guard = self.root / '.claude/guardian'
        self.guard.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        # Aislar TODO proceso del usuario y bloquear red/avisos/reanudación.
        for name, body in {'pgrep': 'exit 0', 'curl': 'exit 99',
                           'claude': 'exit 99', 'notify-send': 'exit 99',
                           'powershell.exe': 'exit 99', 'wt.exe': 'exit 99',
                           'aviso': 'printf "%s\\n" "$1" >> "$GUARDIAN_DIR/avisos"'}.items():
            p = self.bin / name
            p.write_text('#!/usr/bin/env bash\n' + body + '\n')
            p.chmod(0o755)
        (self.guard / 'guardian.conf').write_text('CANAL_AVISO=comando\nAVISO_COMANDO="' + str(self.bin / 'aviso') + '"\n')
        self.env = dict(os.environ, HOME=str(self.root), GUARDIAN_DIR=str(self.guard),
                        GUARDIAN_USAGE=str(self.gb / 'usage.json'), CLAUDE_BIN=str(self.bin / 'claude'),
                        PATH=str(self.bin) + ':' + os.environ['PATH'])
        self.env.pop('GEARBOX_MODEL', None)
        shutil.copyfile(REPO / 'log.sh', self.gb / 'log.sh')
        shutil.copyfile(REPO / 'prices.json', self.gb / 'prices.json')

    def run_script(self, name, *args, payload=None):
        cmd = [os.fsencode(v) for v in ['bash', str(REPO / name), *args]]
        result = subprocess.run(cmd, input=payload, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        self.assertEqual(result.stderr, b'')
        return result.stdout.decode('utf-8', errors='surrogateescape')

    def status(self, **fields):
        payload = {'model': {'id': 'claude-opus-5-5', 'display_name': 'Opus 5.5'},
                   'session_id': 'test-session', **fields}
        return self.run_script('statusline.sh', payload=json.dumps(payload).encode())

    def snapshot(self, pct=96, reset=None, ts=None, sid='test-session', **extra):
        now = int(time.time())
        data = dict(five_hour=pct, reset_five_hour=reset if reset is not None else now + 600,
                    updated_at=ts if ts is not None else now, session_id=sid, **extra)
        (self.gb / 'usage.json').write_text(json.dumps(data))
        return data

    def check(self):
        self.run_script('guardian/guardian.sh', 'check')

    def test_utf8_set_and_all_log_modes(self):
        for raw in (b'\xc3', b'\xff\xfe', b'fin\xc3', b'a\xff\xfeb', 'Español 👁'.encode(), b'"\\\n\r\t\x01'):
            expected = raw.decode('utf-8', 'ignore')
            with self.subTest(raw=raw):
                self.setUp()  # JSONL independiente para cada secuencia de bytes.
                self.run_script('set.sh', 'G2', raw, raw, raw)
                state = json.loads((self.gb / 'state.json').read_text())
                self.assertEqual((state['task'], state['effort'], state['model']), (expected,) * 3)
                self.run_script('log.sh', raw, 'G2', raw, raw, raw)
                self.run_script('log.sh', 'decision', raw, raw, raw, 'ninguno', raw, raw)
                self.run_script('log.sh', 'retrabajo', raw)
                events = [json.loads(line) for line in (self.gb / 'events.jsonl').read_text().splitlines()]
                for record in events:
                    for key in ('task', 'effort', 'model'):
                        self.assertEqual(record.get(key, ''), expected)
                self.assertEqual(events[-1]['action'], expected)
                records = [json.loads(line) for line in (self.gb / 'decisions.jsonl').read_text().splitlines()]
                decision, rework = records[-2:]
                for key in ('gear_actual', 'gear_recomendada', 'task', 'doc', 'accion'):
                    # Una acción vacía usa el default documentado.
                    value = ('recomendar-cambio' if not expected else expected) if key == 'accion' else expected
                    self.assertEqual(decision[key], value)
                self.assertEqual(rework['task'], expected)
        self.run_script('set.sh', 'G2', 'fallback')
        self.assertEqual(json.loads((self.gb / 'state.json').read_text())['model'], expected)

    def freeze_clock(self, now):
        # Reloj determinista solo en procesos hijos de este fixture.
        clock = self.root / 'clock'
        clock.mkdir()
        (clock / 'sitecustomize.py').write_text('import time\ntime.time = lambda: ' + repr(now) + '\n')
        self.env['PYTHONPATH'] = str(clock)
        date = self.bin / 'date'
        date.write_text('#!/usr/bin/env bash\nif [ "$1" = "+%s" ]; then echo ' + str(int(now)) +
                        '; else exec /usr/bin/date "$@"; fi\n')
        date.chmod(0o755)

    def test_model_state_types_and_trailing_newlines(self):
        for saved in (None, False, 42, [], {}, '', 'Sonnet\n\n'):
            with self.subTest(saved=saved):
                expected = saved if isinstance(saved, str) else ''
                (self.gb / 'state.json').write_text(json.dumps({'model': saved}))
                self.run_script('log.sh', 'decision', 'G2', 'G2', 'fallback')
                records = [json.loads(line) for line in (self.gb / 'decisions.jsonl').read_text().splitlines()]
                self.assertEqual(records[-1]['model'], expected)
                self.run_script('set.sh', 'G2', 'fallback')
                self.assertEqual(json.loads((self.gb / 'state.json').read_text())['model'], expected)
                event = json.loads((self.gb / 'events.jsonl').read_text().splitlines()[-1])
                self.assertEqual(event.get('model', ''), expected)

    def test_log_model_environment_all_modes(self):
        for raw in (b'\xc3', b'x\xff\xfey', 'Español 👁'.encode(), b'"\\\n\t\x01'):
            with self.subTest(raw=raw):
                self.env['GEARBOX_MODEL'] = os.fsdecode(raw)
                expected = raw.decode('utf-8', 'ignore')
                self.run_script('log.sh', 'set', 'G2', 'event', 'auto')
                self.run_script('log.sh', 'decision', 'G2', 'G2', 'decision')
                self.run_script('log.sh', 'retrabajo', 'rework')
                event = json.loads((self.gb / 'events.jsonl').read_text().splitlines()[-1])
                self.assertEqual(event.get('model', ''), expected)
                records = [json.loads(line) for line in (self.gb / 'decisions.jsonl').read_text().splitlines()]
                for record, task in zip(records[-2:], ('decision', 'rework')):
                    self.assertEqual(record['model'], expected)
                    self.assertEqual(record['task'], task)

    def test_status_null_effort_and_invalid_utf8(self):
        for effort in (None, '', [], 7, False):
            (self.gb / 'state.json').write_text(json.dumps({'effort': effort}))
            self.assertIn(' · ? · ', self.status())
        payload = b'{"model":{"display_name":"Opus \xff5.5"},"effort":"hi\xfegh"}'
        text = self.run_script('statusline.sh', payload=payload)
        self.assertIn('Opus 5.5 · high · ', text)
        # También cadenas JSON con un surrogate aislado, no solo argv inválido.
        text = self.run_script('statusline.sh', payload=br'{"model":{"display_name":"Opus \uD8005.5"}}')
        self.assertIn('Opus 5.5 · ? · ', text)

    def test_session_id_invalid_utf8_and_surrogates(self):
        cases = [(b'pre\xff\xfe-post', 'pre-post'), (b'fin\xc3', 'fin'),
                 (br'pre\uD800-post', 'pre-post'), (br'pre\uDCFF-post', 'pre-post'),
                 (b'\xff', ''), (br'\uD800', ''), ('sesión 👁'.encode(), 'sesión 👁')]
        # Probar escritor y lector por separado: un usage.json previo también
        # puede contener surrogates aunque el statusline ya esté corregido.
        for source in ('statusline', 'snapshot'):
            for raw, expected in cases:
                with self.subTest(source=source, raw=raw):
                    self.setUp()
                    self.freeze_clock(1700000000.8)
                    self.env['PYTHONIOENCODING'] = 'utf-8:strict'
                    if source == 'statusline':
                        payload = (b'{"session_id":"' + raw +
                                   b'","rate_limits":{"five_hour":{"used_percentage":96,'
                                   b'"resets_at":1700000600}}}')
                        self.run_script('statusline.sh', payload=payload)
                        data = json.loads((self.gb / 'usage.json').read_text())
                        self.assertEqual(data['session_id'], expected)
                    else:
                        sid = json.loads('"' + raw.decode('utf-8', 'surrogateescape') + '"')
                        self.snapshot(sid=sid, ts=1700000000.5, reset=1700000600)
                    self.assertEqual(self.run_script('guardian/guardian.sh', 'registrar'),
                                     '✓ vigilando ' + expected + '\n')
                    self.assertEqual((self.guard / 'estado/session_id').read_text(), expected + '\n')
                    self.check()
                    self.assertEqual((self.guard / 'estado/pausa_cupo').exists(), bool(expected))

    def test_guardian_legacy_pause_requires_sample_stamp(self):
        self.freeze_clock(1700000000.8)
        state = self.guard / 'estado'
        state.mkdir()
        pause = state / 'pausa_cupo'
        content = "SID='test-session'\nRESET='1'\nDESDE='00:00'\n"
        pause.write_text(content)
        self.snapshot(pct=10, ts=1700000000.5, reset=1700000600)
        self.check()
        self.assertEqual(pause.read_text(), content)
        self.assertFalse((state / 'pendiente').exists())
        self.assertFalse((self.guard / 'avisos').exists())

    def test_guardian_unknown_cupo_cli(self):
        text = self.run_script('guardian/guardian.sh', 'cupo')
        self.assertIn('cupo 5 h: desconocido', text)
        self.assertIn('cupo 7 días: desconocido', text)
        self.assertNotIn('%', text)
        self.snapshot(pct=25)
        text = self.run_script('guardian/guardian.sh', 'cupo')
        self.assertIn('cupo 5 h usado : 25%', text)
        self.assertIn('cupo 7 días: desconocido', text)

    def test_expired_fractional_reset_is_hidden(self):
        self.freeze_clock(1000.8)
        text = self.status(rate_limits={'five_hour': {'used_percentage': 99, 'resets_at': 1000.5},
                                       'seven_day': {'used_percentage': 20, 'resets_at': 1000.9}})
        self.assertNotIn('% 5h', text)
        self.assertIn('20% 7d', text)
        data = json.loads((self.gb / 'usage.json').read_text())
        self.assertNotIn('five_hour', data)
        self.assertEqual(data['updated_at'], 1000.8)

    def test_expired_windows_are_hidden(self):
        text = self.status(rate_limits={'five_hour': {'used_percentage': 99, 'resets_at': time.time() - 1},
                                       'seven_day': {'used_percentage': 88, 'resets_at': time.time() - 1}})
        self.assertNotIn('% 5h', text)
        self.assertNotIn('% 7d', text)
        self.assertNotIn('considera bajar', text)

    def test_independent_windows_and_atomic_snapshot(self):
        text = self.status(rate_limits={'five_hour': {'used_percentage': 95.9, 'resets_at': time.time() + 600},
                                       'seven_day': {'used_percentage': 88, 'resets_at': time.time() - 1}})
        self.assertIn('95% 5h', text)
        self.assertNotIn('% 7d', text)
        data = json.loads((self.gb / 'usage.json').read_text())
        self.assertEqual(data['five_hour'], 95)
        self.assertNotIn('seven_day', data)
        self.assertEqual((self.gb / 'usage.json').stat().st_mode & 0o777, 0o600)
        self.check()
        self.assertTrue((self.guard / 'estado/pausa_cupo').exists())
        self.status()
        self.assertNotIn('five_hour', json.loads((self.gb / 'usage.json').read_text()))
        self.check()
        self.assertFalse((self.guard / 'estado/pendiente').exists())

    def test_invalid_windows(self):
        for value in ({'used_percentage': 99}, {'used_percentage': 101, 'resets_at': time.time()+600},
                      {'used_percentage': True, 'resets_at': time.time()+600},
                      {'used_percentage': 99, 'resets_at': None}, 'invalid'):
            with self.subTest(value=value):
                self.assertNotIn('% 5h', self.status(rate_limits={'five_hour': value}))

    def test_guardian_rejects_stale_future_expired_missing_stamp(self):
        for change in ({'ts': time.time()-301}, {'ts': time.time()+60},
                       {'reset': time.time()-1}, {'ts': 'invalid'}):
            with self.subTest(change=change):
                self.snapshot(**change)
                self.check()
                self.assertFalse((self.guard / 'estado/pausa_cupo').exists())
        (self.gb / 'usage.json').write_text('{"five_hour":99}')
        self.check()
        self.assertFalse((self.guard / 'estado/pausa_cupo').exists())

    def test_guardian_no_renewal_or_alternation_from_expired_data(self):
        state = self.guard / 'estado'
        state.mkdir()
        (state / 'pausa_cupo').write_text("SID='test-session'\nRESET='1'\nDESDE='00:00'\nLECTURA='1'\n")
        self.snapshot(reset=time.time()-1, ts=time.time()-600)
        for _ in range(3):
            self.check()
        self.assertTrue((state / 'pausa_cupo').exists())
        self.assertFalse((state / 'pendiente').exists())
        self.assertFalse((self.guard / 'avisos').exists())

    def test_renewal_requires_new_sample_same_session(self):
        now = int(time.time())
        self.snapshot(ts=now-2)
        self.check()
        self.snapshot(pct=10, ts=now-2)
        self.check()
        self.assertFalse((self.guard / 'estado/pendiente').exists())
        self.snapshot(pct=10, sid='other-session')
        self.check()
        self.assertFalse((self.guard / 'estado/pendiente').exists())
        self.snapshot(pct=10)
        self.check()
        self.assertEqual((self.guard / 'estado/pendiente').read_text().strip(), 'test-session')
        self.check()
        self.assertEqual(len((self.guard / 'avisos').read_text().splitlines()), 2)

    def test_registered_session_not_replaced(self):
        state = self.guard / 'estado'
        state.mkdir()
        (state / 'session_id').write_text('registered-session')
        self.snapshot()
        self.check()
        self.assertFalse((state / 'pausa_cupo').exists())

    def test_prices_all_models_and_haiku_boundary(self):
        for label, mid, ratio in [('Fable 5.1','claude-fable-5-1','5'), ('Opus 5.5','claude-opus-5-5','2'),
                                  ('Sonnet 5.5','claude-sonnet-5-5','1')]:
            with self.subTest(model=mid):
                self.assertIn('≈'+ratio+'x', self.status(model={'display_name':label, 'id':mid}))
        for n, ratio in [(100000,'0.05'), (100001,'0.25')]:
            self.assertIn('≈'+ratio+'x', self.status(model={'display_name':'Haiku 5.5','id':'claude-haiku-5-5'},
                                                    context_window={'total_input_tokens':n}))
        self.assertNotIn('≈', self.status(model={'display_name':'Haiku 5.5','id':'claude-haiku-5-5'}))
        self.assertNotIn('≈', self.status(model={'display_name':'Opus 5','id':'claude-opus-5'}))
        self.assertIn(' · ? · ', self.status())


if __name__ == '__main__':
    unittest.main(verbosity=2)
