#!/usr/bin/env python3
"""Sync or verify exact, already-published Feedbacks native plugin bundles."""
import argparse
import hashlib
import io
import json
import pathlib
import re
import shutil
import stat
import subprocess
import time
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_REPOSITORY = 'https://github.com/Softinator-TechLabs/feedbacks-oss'
TARGETS = ('codex', 'claude')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def asset(name, version, directory):
    if directory:
        return (directory / name).read_bytes()
    url = f'{SOURCE_REPOSITORY}/releases/download/v{version}/{name}'
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                data = response.read(16 * 1024 * 1024 + 1)
            require(len(data) <= 16 * 1024 * 1024, f'{name}: oversized asset')
            return data
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def bundles(version, revision, directory):
    checksums = {}
    for line in asset('SHA256SUMS', version, directory).decode('utf-8').splitlines():
        checksum, name = line.split(maxsplit=1)
        require(re.fullmatch(r'[a-f0-9]{64}', checksum), 'Invalid release checksum')
        require(name not in checksums, 'Duplicate release checksum entry')
        checksums[name] = checksum
    release_bytes = asset('release.json', version, directory)
    require(digest(release_bytes) == checksums['release.json'], 'release.json checksum mismatch')
    release = json.loads(release_bytes)
    require(release['sha'] == revision, 'Canonical source revision mismatch')
    require(release['tag'] == f'v{version}', 'Canonical source tag mismatch')
    require(release['versions']['plugin'] == version, 'Canonical plugin version mismatch')
    result = {}
    for target in TARGETS:
        name = f'feedbacks-{target}-plugin-{version}.zip'
        data = asset(name, version, directory)
        checksum = digest(data)
        require(checksum == checksums[name], f'{name}: release checksum mismatch')
        release_entry = next(item for item in release['assets'] if item['name'] == name)
        require(release_entry['sha256'] == checksum and release_entry['bytes'] == len(data), f'{name}: release metadata mismatch')
        entries = {}
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            require(sum(item.file_size for item in archive.infolist()) <= 32 * 1024 * 1024, f'{name}: oversized contents')
            for info in archive.infolist():
                path = pathlib.PurePosixPath(info.filename)
                require(not info.is_dir(), f'{name}: unexpected directory entry')
                require(not path.is_absolute() and '..' not in path.parts and '\\' not in info.filename, f'{name}: unsafe path')
                require(str(path) == info.filename and info.filename not in entries, f'{name}: duplicate/noncanonical path')
                require(not any(part in ('.git', '.local', 'node_modules') or part.startswith('.env') for part in path.parts), f'{name}: private component')
                require(not stat.S_ISLNK(info.external_attr >> 16), f'{name}: symlink')
                entries[info.filename] = archive.read(info)
        native = f'.{target}-plugin/plugin.json'
        manifest = json.loads(entries[native])
        require(manifest['name'] == 'feedbacks' and manifest['version'] == version, f'{target}: native identity/version mismatch')
        if target == 'codex':
            portable = json.loads(entries['plugin.json'])
            require(portable['$schema'] == 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json', 'Portable manifest schema mismatch')
            require(portable['name'] == manifest['name'] and portable['version'] == version, 'Portable/native identity mismatch')
        for filename, contents in entries.items():
            if filename.endswith('.json'):
                json.loads(contents)
            if filename.endswith('/SKILL.md'):
                require(contents.decode('utf-8').startswith('---\nname: '), f'{filename}: missing skill metadata')
        for filename in ('mcp.mjs', 'BUILD.json', 'LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md', 'skills/review-feedback/SKILL.md', 'skills/manage-feedbacks-context/SKILL.md'):
            require(filename in entries, f'{target}: missing required component {filename}')
        result[target] = {'asset': name, 'sha256': checksum, 'bytes': len(data), 'file_count': len(entries), 'entries': entries}
    require(result['codex']['entries']['mcp.mjs'] == result['claude']['entries']['mcp.mjs'], 'Native runtime bundles differ')
    return result


def repository_files():
    output = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT)
    return sorted(set(name for name in output.decode('utf-8').split('\0') if name and name != 'SOURCE.json'))


def inventory():
    files = []
    for name in repository_files():
        path = ROOT / name
        require(path.is_file() and not path.is_symlink(), f'Not a regular repository file: {name}')
        files.append({'path': name, 'sha256': digest(path.read_bytes())})
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('sync', 'check'))
    parser.add_argument('--version')
    parser.add_argument('--source-revision')
    parser.add_argument('--source-ci')
    parser.add_argument('--assets-directory', type=pathlib.Path, help='Verified OSS release download directory; otherwise download public assets')
    args = parser.parse_args()
    if args.command == 'sync':
        require(args.version and re.fullmatch(r'\d+\.\d+\.\d+', args.version), 'Supply a release version')
        require(args.source_revision and re.fullmatch(r'[a-f0-9]{40}', args.source_revision), 'Supply a full source revision')
        require(args.source_ci and re.fullmatch(r'https://github.com/Softinator-TechLabs/feedbacks-oss/actions/runs/\d+', args.source_ci), 'Supply exact-source CI URL')
        source = {'version': args.version, 'source_repository': SOURCE_REPOSITORY, 'source_revision': args.source_revision, 'source_tag': f'v{args.version}', 'source_ci': args.source_ci, 'packaging': 'Exact published canonical native Claude Code/Codex bundles; catalogs point to runtime subdirectories. No private launch material.'}
    else:
        source = json.loads((ROOT / 'SOURCE.json').read_text())
        require(source['source_repository'] == SOURCE_REPOSITORY, 'Unexpected source repository')
    packaged = bundles(source['version'], source['source_revision'], args.assets_directory)
    metadata = {target: {key: value for key, value in bundle.items() if key != 'entries'} for target, bundle in packaged.items()}
    for target, bundle in packaged.items():
        destination = ROOT / target / 'feedbacks'
        if args.command == 'sync':
            shutil.rmtree(destination)
            for name, contents in bundle['entries'].items():
                path = destination / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(contents)
        else:
            actual = {str(path.relative_to(destination)): path.read_bytes() for path in destination.rglob('*') if path.is_file()}
            require(actual == bundle['entries'], f'{target}: repository contents differ from canonical published ZIP')
        catalog_path = '.agents/plugins/marketplace.json' if target == 'codex' else '.claude-plugin/marketplace.json'
        catalog = json.loads((ROOT / catalog_path).read_text())
        require(catalog['name'] == 'feedbacks' and len(catalog['plugins']) == 1, f'{target}: marketplace identity mismatch')
        plugin = catalog['plugins'][0]
        require(plugin['name'] == 'feedbacks', f'{target}: marketplace plugin identity mismatch')
        catalog_source = plugin['source']['path'] if target == 'codex' else plugin['source']
        require(catalog_source == f'./{target}/feedbacks', f'{target}: marketplace source mismatch')
    for name in ('LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md'):
        canonical = packaged['codex']['entries'][name]
        require(canonical == packaged['claude']['entries'][name], f'{name}: native licensing differs')
        if args.command == 'sync':
            (ROOT / name).write_bytes(canonical)
        else:
            require((ROOT / name).read_bytes() == canonical, f'{name}: root licensing differs from native bundles')
    if args.command == 'sync':
        source['bundles'] = metadata
        source['files'] = inventory()
        (ROOT / 'SOURCE.json').write_text(json.dumps(source, indent=2) + '\n')
    else:
        require(source['bundles'] == metadata, 'SOURCE bundle metadata mismatch')
        require(source['files'] == inventory(), 'SOURCE file inventory mismatch; review then regenerate with sync')
    print(json.dumps({'status': 'passed', 'command': args.command, 'version': source['version'], 'source_revision': source['source_revision'], 'bundles': metadata, 'repository_files': len(source['files'])}, indent=2))


if __name__ == '__main__':
    main()
