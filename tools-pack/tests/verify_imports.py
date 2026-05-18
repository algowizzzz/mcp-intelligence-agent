"""REQ-17 Story 4 post-batch — verify every tools-pack tool imports cleanly
and its config JSON points at a class that exists.

Run with:
    PYTHONPATH=$(pwd)/tools-pack:$(pwd)/sajhamcpserver-upstream \
      ./venv/bin/python tools-pack/tests/verify_imports.py
"""
import importlib
import json
import sys
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parent.parent.parent
    configs = sorted((repo / 'tools-pack' / 'configs').glob('*.json'))
    print(f'tools-pack/configs: {len(configs)} JSON tool configs')
    print('=' * 78)

    ok = 0
    fail = 0
    fails: list = []

    for cfg_path in configs:
        try:
            cfg = json.loads(cfg_path.read_text())
        except Exception as e:
            fail += 1
            fails.append((cfg_path.name, f'JSON parse error: {e}'))
            print(f'  [FAIL] {cfg_path.name}  JSON parse: {e}')
            continue

        impl = cfg.get('implementation', '')
        if not impl:
            fail += 1
            fails.append((cfg_path.name, 'no implementation field'))
            print(f'  [FAIL] {cfg_path.name}  no `implementation` field')
            continue

        mod_path, _, cls_name = impl.rpartition('.')
        try:
            mod = importlib.import_module(mod_path)
            cls = getattr(mod, cls_name, None)
            if cls is None:
                raise AttributeError(f'{cls_name} not in {mod_path}')
            # Check it extends BaseMCPTool (upstream's base class)
            try:
                from sajha.tools.base_mcp_tool import BaseMCPTool
                if not issubclass(cls, BaseMCPTool):
                    raise TypeError(f'{cls_name} does not extend BaseMCPTool')
            except ImportError:
                pass  # upstream not on path during sanity check
            # Try to instantiate with the config
            inst = cls(cfg)
            # Confirm execute exists
            if not hasattr(inst, 'execute'):
                raise AttributeError('no execute() method')
            ok += 1
            print(f'  [OK]   {cfg_path.name:55s} → {impl}')
        except Exception as e:
            fail += 1
            fails.append((cfg_path.name, f'{type(e).__name__}: {e}'))
            print(f'  [FAIL] {cfg_path.name:55s} → {impl}  ({type(e).__name__}: {str(e)[:80]})')

    print()
    print('=' * 78)
    print(f'OK:    {ok} / {len(configs)}')
    print(f'FAIL:  {fail} / {len(configs)}')
    if fails:
        print('\nFailures:')
        for n, msg in fails:
            print(f'  - {n}: {msg}')
    return 0 if fail == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
