"""Install pinned Linux x86_64 lab tools and verify their release hashes."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

root=Path(__file__).resolve().parent.parent
versions=json.loads((root/'scripts/tools.json').read_text())
destination=root/'.tools/bin'
destination.mkdir(parents=True,exist_ok=True)
for name in sys.argv[1:]:
    tool=versions[name]
    content=subprocess.check_output(['curl','--fail','--silent','--show-error','--location',
        '--retry','3','--max-time','180',tool['url']])
    if hashlib.sha256(content).hexdigest()!=tool['sha256']:
        raise SystemExit('Checksum mismatch for '+name)
    if tool['archive']:
        with tarfile.open(fileobj=io.BytesIO(content),mode='r:gz') as archive:
            member=next(m for m in archive.getmembers() if m.isfile() and Path(m.name).name==name)
            content=archive.extractfile(member).read()
    path=destination/name
    path.write_bytes(content)
    path.chmod(0o755)
    print(f'Installed {name} {tool["version"]}; SHA256 verified',flush=True)
