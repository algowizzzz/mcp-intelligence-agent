"""
One-time migration: JSON flat files → PostgreSQL.
REQ-07 Phase 2: users, workers, connectors, threads.

Run from project root:
    python scripts/migrate_json_to_pg.py

Safe to run multiple times (upsert logic — will not duplicate rows).
"""
import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'sajhamcpserver'))

from sajha.db import repo

USERS_FILE      = pathlib.Path('sajhamcpserver/config/users.json')
WORKERS_FILE    = pathlib.Path('sajhamcpserver/config/workers.json')
CONNECTORS_FILE = pathlib.Path('sajhamcpserver/config/connectors.json')
THREADS_FILE    = pathlib.Path('sajhamcpserver/data/threads.jsonl')
AUDIT_FILE      = pathlib.Path('sajhamcpserver/data/audit/tool_calls.jsonl')


async def migrate_users():
    data = json.loads(USERS_FILE.read_text())
    users = data.get('users', [])
    ok = 0
    for u in users:
        try:
            await repo.upsert_user({
                'user_id':             u['user_id'],
                'username':            u.get('user_id'),          # username = user_id currently
                'display_name':        u.get('display_name', u.get('user_id', '')),
                'password_hash':       u.get('password_hash', ''),
                'role':                u.get('role', 'user'),
                'worker_id':           u.get('worker_id'),
                'enabled':             u.get('enabled', True),
                'onboarding_complete': u.get('onboarding_complete', False),
            })
            ok += 1
        except Exception as e:
            print(f'  WARN user {u.get("user_id")}: {e}')
    print(f'Users:   {ok}/{len(users)} migrated')


async def migrate_workers():
    data = json.loads(WORKERS_FILE.read_text())
    workers = data.get('workers', [])
    ok = 0
    for w in workers:
        try:
            await repo.upsert_worker({
                'worker_id':        w['worker_id'],
                'name':             w.get('name', w['worker_id']),
                'description':      w.get('description'),
                'system_prompt':    w.get('system_prompt'),
                'enabled_tools':    w.get('enabled_tools', ['*']),
                'domain_data_path': w.get('domain_data_path'),
                'verified_wf_path': w.get('workflows_path'),
                'connector_scope':  w.get('connector_scope', {}),
                'enabled':          w.get('enabled', True),
            })
            ok += 1
        except Exception as e:
            print(f'  WARN worker {w.get("worker_id")}: {e}')
    print(f'Workers: {ok}/{len(workers)} migrated')


async def migrate_connectors():
    if not CONNECTORS_FILE.exists():
        print('Connectors: file not found, skipping')
        return
    data = json.loads(CONNECTORS_FILE.read_text())
    ok = 0
    for ctype, cdata in data.items():
        if not isinstance(cdata, dict):
            continue
        try:
            await repo.upsert_connector(ctype, {
                'display_name':   cdata.get('display_name', ctype),
                'status':         cdata.get('status', 'not_configured'),
                'enabled':        cdata.get('enabled', False),
                'has_credentials': bool(cdata.get('client_secret') or cdata.get('api_token')),
                # NOTE: credentials are NOT migrated here — they contain secrets.
                # Re-enter via admin UI after migration to store encrypted.
            })
            ok += 1
        except Exception as e:
            print(f'  WARN connector {ctype}: {e}')
    print(f'Connectors: {ok} migrated (credentials NOT migrated — re-enter via admin UI)')


async def migrate_threads():
    if not THREADS_FILE.exists():
        print('Threads: file not found, skipping')
        return
    lines = THREADS_FILE.read_text().splitlines()
    ok = 0
    for line in lines:
        try:
            entry = json.loads(line)
            tid = entry.get('thread_id')
            uid = entry.get('user_id')
            wid = entry.get('worker_id')
            if tid and uid and wid:
                await repo.register_thread(tid, uid, wid)
                ok += 1
        except Exception as e:
            print(f'  WARN thread: {e}')
    print(f'Threads: {ok}/{len(lines)} migrated')


async def migrate_audit(limit: int = 5000):
    """Migrate most recent N audit events from JSONL to PostgreSQL."""
    if not AUDIT_FILE.exists():
        print('Audit: file not found, skipping')
        return
    lines = AUDIT_FILE.read_text().splitlines()
    recent = lines[-limit:]
    ok = 0
    from sajha.db.engine import AsyncSessionLocal
    from sajha.db.models import AuditEvent
    from datetime import datetime, timezone
    async with AsyncSessionLocal() as db:
        for line in recent:
            try:
                entry = json.loads(line)
                row = AuditEvent(
                    event_type='tool_call',
                    user_id=entry.get('user_id') or None,
                    worker_id=entry.get('worker_id') or None,
                    tool_name=entry.get('tool_name'),
                    tool_result_ok=(entry.get('status') == 'success'),
                    elapsed_ms=int(entry.get('duration_ms', 0)),
                    detail={'status': entry.get('status')},
                    created_at=datetime.fromisoformat(
                        entry['timestamp'].rstrip('Z')
                    ).replace(tzinfo=timezone.utc) if entry.get('timestamp') else datetime.now(timezone.utc),
                )
                db.add(row)
                ok += 1
            except Exception as e:
                print(f'  WARN audit: {e}')
        await db.commit()
    print(f'Audit:   {ok}/{len(recent)} events migrated (most recent {limit})')


async def main():
    print('=== B-Pulse JSON → PostgreSQL Migration ===\n')
    await migrate_workers()    # workers first (users FK to workers)
    await migrate_users()
    await migrate_connectors()
    await migrate_threads()
    await migrate_audit()
    print('\nMigration complete.')


if __name__ == '__main__':
    asyncio.run(main())
