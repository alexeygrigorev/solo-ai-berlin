"""Local-only inspection/export. No remote admin route, refunds or emails."""
from __future__ import annotations
import argparse
import json
import store

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('command', choices=['summary', 'export'])
args = parser.parse_args()
applications = store.list_applications()
if args.command == 'summary':
    paid, flagged = store.payment_counts()
    print('Applications:', len(applications))
    print('Recorded paid sessions:', paid)
    print('Flagged payments:', flagged)
    print('These counts do not imply accepted members or confirmed seats.')
else:
    for item in applications:
        print(json.dumps(item, ensure_ascii=False, default=str))
