#!/usr/bin/env python3
"""Verify standalone release assets and publish a coordinated suite manifest."""
import argparse,hashlib,importlib.util,json,re,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('suite',ROOT/'tools/suite.py');suite=importlib.util.module_from_spec(spec);spec.loader.exec_module(suite)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tag',default='suite-v0.1.0');p.add_argument('--download-assets',action='store_true');p.add_argument('--publish',action='store_true');a=p.parse_args()
 if not re.fullmatch(r'suite-v\d+\.\d+\.\d+',a.tag):raise SystemExit('Invalid suite version tag')
 repos,apps,state=suite.load()
 if a.download_assets:
  for repo in repos.values():
   if repo.get('mode')=='self':continue
   root=suite.checkout(repo,state)
   for name in repo.get('artifacts',[]):
    dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest()==repo['artifact_sha256'][name]:continue
    url='https://github.com/design-nexus/'+repo['name']+'/releases/download/'+repo['release_tag']+'/'+dest.name
    subprocess.run(['curl','-fsSL','--retry','3','--output',str(dest),url],check=True)
 if suite.release_check(repos,apps,state):raise SystemExit('Release checks failed')
 dest=ROOT/'target/suite-release';dest.mkdir(parents=True,exist_ok=True)
 notes=['# Nyx '+a.tag,'','Versioned, checksummed independent application releases.','','## Applications','']
 for app in sorted(apps.values(),key=lambda x:x['id']):
  repo=repos[app['repository']];notes.append('- ['+app['id']+' '+repo['release_tag']+'](https://github.com/design-nexus/'+repo['name']+'/releases/tag/'+repo['release_tag']+')')
 (dest/'CHANGELOG.md').write_text('\n'.join(notes)+'\n')
 for name in ['suite.toml','build-environment.json']:shutil.copy2(ROOT/name,dest/name)
 assets=[dest/'suite.toml',dest/'build-environment.json',dest/'CHANGELOG.md'];checks=dest/'SHA256SUMS';checks.write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in assets));assets.append(checks)
 if a.publish:
  subprocess.run(['gh','release','create',a.tag,*map(str,assets),'--repo','design-nexus/nyx','--target',suite.revision(ROOT),'--title','Nyx '+a.tag,'--notes-file',str(dest/'CHANGELOG.md')],check=True)
if __name__=='__main__':main()
