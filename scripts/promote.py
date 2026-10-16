"""Promote only a full commit SHA; no YAML dependency required."""
import re
import sys
from pathlib import Path
sha = sys.argv[1]
if not re.fullmatch(r'[0-9a-f]{40}', sha):
    raise SystemExit('Expected a full Git commit SHA')
path = Path('gitops/release.yaml')
content, count = re.subn(r'(?m)^(    tag: ).*$', lambda match: match[1] + sha, path.read_text())
if count != 2:
    raise SystemExit('Expected exactly two image tags')
path.write_text(content)
