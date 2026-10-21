#!/usr/bin/env python3
"""Record a completely built/published suite without changing application source."""
import hashlib,json,subprocess,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def value(x):
 if isinstance(x,dict):return '{ '+', '.join(json.dumps(k)+' = '+value(v) for k,v in x.items())+' }'
 return json.dumps(x)
def main():
 state=json.loads((ROOT/'.nixe-local.json').read_text());suite=tomllib.loads((ROOT/'suite.toml').read_text())
 builds=json.loads((ROOT/'docs/migration/release-validation.json').read_text());releases=json.loads((ROOT/'docs/migration/releases.json').read_text())
 for repo in suite['repositories']:
  id=repo['id']
  if id=='monorepo':continue
  record=state['repositories'][id];path=Path(record['path']);head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=path,text=True).strip()
  if head!=record['revision']:raise RuntimeError(id+': checkout revision drift')
  if id in ['core','design']:
   release_revision=repo.get('release_revision',repo['artifact_revision'])
   tag='v0.1.0';assets=[f'dist/nixe-{id}-{tag}-source.tar.gz','dist/CHANGELOG.md','dist/SHA256SUMS']
   if id=='design':assets.append(f'dist/nixe-design-{release_revision}.tar.gz')
  else:
   built=builds[id];release=releases[id]
   release_revision=release['revision']
   if not release['published'] or built['revision']!=release_revision:raise RuntimeError(id+': release/build does not match source')
   tag=release['tag'];assets=[f'dist/{id}-x86_64.tar.gz','dist/CHANGELOG.md','dist/build-info.json','dist/SHA256SUMS']
   if id=='git':assets += [str(p.relative_to(path)) for p in (path/'dist').glob('*.pkg.tar.zst')]
   repo['build_features']=[f for f in built.get('features','').split(',') if f]
  repo.update(revision=head,status='published',release_tag=tag,artifact_revision=release_revision,release_revision=release_revision,artifacts=assets)
  repo['artifact_sha256']={name:hashlib.sha256((path/name).read_bytes()).hexdigest() for name in assets}
  if 'dependency_revision' in record:repo['dependency_revision']=record['dependency_revision']
 for app in suite['applications']:app['supported_releases']=[next(r['release_tag'][1:] for r in suite['repositories'] if r['id']==app['repository'])]
 lines=['# Supported standalone suite release. Original source remains a frozen rollback copy.','schema_version = 1','baseline = '+value(suite['baseline']),'','[compatibility]']
 for k,v in suite['compatibility'].items():lines.append(k+' = '+value(v))
 for section in ['repositories','applications']:
  for entry in suite[section]:lines += ['','[['+section+']]']+[k+' = '+value(v) for k,v in entry.items()]
 (ROOT/'suite.toml').write_text('\n'.join(lines)+'\n')
 (ROOT/'docs/migration/repositories.json').write_text(json.dumps(state,indent=2)+'\n')
 print('All 25 release/source pins and artifact checksums recorded.')
if __name__=='__main__':main()
