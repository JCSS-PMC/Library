"""Build the static catalogue from reviewed metadata.

Run with the Jupyter Book Python environment. Pass --archive PATH on first use
to copy missing originals from the local collection. Existing bytes are checked
against the source register and are never silently replaced. --check verifies
generated pages and original files without changing them.
"""
import argparse
import csv
import hashlib
import json
from html import escape
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
TITLES = {
    'reports': 'Reports and guidance',
    'events': 'Events and meetings',
    'education': 'Education',
    'notices': 'Publication notices and press releases',
}
INTRODUCTIONS = {
    'reports': 'Reports are grouped by subject. Each entry provides its reading edition and original PDF, with source dates and draft or edition details where applicable.',
    'events': 'Papers, abstracts, conclusions, presentations, and programmes are grouped by event, with the newest first. Related resources share an entry. Announcements and programmes describe the activity proposed in the source; they do not establish that it took place. Registration details belong to the stated event date. Draft and preliminary versions retain their original labels.',
    'education': 'Course documents are collected under their activity. The infrastructure integrity webinar series brings together session posters and supplementary reading. Activities are ordered with the newest first, and webinar sessions follow their scheduled sequence.',
    'notices': 'Publication information and press releases are ordered by year, with the newest first. A publication notice describes a work and does not provide its full text.',
}


def load_entries():
    return json.loads((ROOT / 'catalogue/entries.json').read_text(encoding='utf-8'))


def load_works():
    """Load reader-facing groupings separately from immutable file provenance."""
    return json.loads((ROOT / 'catalogue/works.json').read_text(encoding='utf-8'))


def check_work_coverage(works, entries):
    """Require exactly one catalogue home for each source file."""
    by_file = {entry['local_file']: entry for entry in entries}
    assigned = [resource['file'] for work in works for resource in work['resources']]
    assert len(assigned) == len(set(assigned)) == len(entries)
    assert set(assigned) == set(by_file)
    assert len({work['id'] for work in works}) == len(works)
    for work in works:
        assert work['resources'] and work['title'] and work['document_type']
        for resource in work['resources']:
            assert by_file[resource['file']]['group'] == work['group']
            assert resource['label'].startswith('Download ')


def original_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_size_label(entry):
    """Show decimal file sizes without changing or recompressing originals."""
    if entry.get('external_original'):
        return 'Hosted by the original provider'
    size = (ROOT / entry['original']).stat().st_size
    return f'{size / 1_000_000:.1f} MB' if size >= 1_000_000 else f'{size / 1_000:.1f} kB'


def resource_lines(work, by_file):
    """Keep secondary files together while leaving every download accessible."""
    lines = []
    resources = sorted(work['resources'], key=lambda resource: resource.get('secondary', False))
    secondary_open = False
    for resource in resources:
        if resource.get('secondary') and not secondary_open:
            lines += [':::{div} library-secondary', '', '**Other activity documents**', '']
            secondary_open = True
        entry = by_file[resource['file']]
        if entry.get('external_original'):
            links = [f"[{resource['label']}]({entry['source_url']})"]
        else:
            links = [f"{{download}}`{resource['label']} <../{entry['original']}>`"]
        if entry['reader']:
            links.insert(0, f"[{resource['online_label']}](../{entry['reader']})")
        details = []
        if entry['pages']:
            unit = 'page' if entry['pages'] == '1' else 'pages'
            details.append(f"{entry['pages']} {unit}")
        details.append(file_size_label(entry))
        links.append('<span class="library-file-details">' + ' · '.join(details) + '</span>')
        lines += [' · '.join(links), '']
    if secondary_open:
        lines += [':::', '']
    if work.get('resource_note'):
        lines += [f'<p class="library-file-details">{escape(work["resource_note"])}</p>', '']
    return lines


def permalink(work):
    """Provide a compact permanent link with a descriptive accessible name."""
    label = escape('Permanent link to ' + work['title'], quote=True)
    return f'<a class="library-permalink" href="#{work["id"]}" aria-label="{label}">¶</a>'


def metadata_lines(work, show_date=True):
    """Separate source roles and status without repeating the surrounding heading."""
    values = []
    if show_date and work['date']:
        values.append(f'{work["date_kind"]}: {work["date"]}')
    authors = work['authors'] or work.get('organisation', '')
    if authors:
        values.append(authors.replace('Joint Committee on Structural Safety', 'JCSS'))
    if work.get('editors'):
        values.append('Editor: ' + work['editors'])
    document_type = work['document_type']
    if document_type not in {'Report', 'Webinar'} and document_type.lower() not in work['title'].lower():
        values.append(document_type)
    if work.get('status'):
        values.append(work['status'])
    lines = []
    if values:
        lines += [':::{div} library-metadata', '', ' · '.join(values), '', ':::', '']
    if work.get('note'):
        lines += [work['note'], '']
    return lines


def education_page(entries, works):
    """Keep direct course downloads and stable links to relocated sessions."""
    by_file = {entry['local_file']: entry for entry in entries}
    courses = sorted((work for work in works if work['document_type'] == 'Course'),
                     key=lambda work: work['date'], reverse=True)
    sessions = sorted((work for work in works if work['page'] == 'catalogue/webinars-2022-2023'),
                      key=lambda work: work['date'])
    lines = ['# Education', '', 'Find course information, webinar sessions, and supplementary reading. Courses are listed newest first. Original documents remain available directly from each entry.', '', '## Courses', '',
             'These documents describe courses as announced. Dates identify the proposed activity, and registration instructions belong to that date. The downloads provide course information rather than lecture materials.', '']
    for work in courses:
        lines += [f"```{{div}} library-work", f":name: {work['id']}", '',
                  f"**{work['date']} — {work['title']}** {permalink(work)}", '']
        if work.get('note'):
            lines += [work['note'], '']
        lines += resource_lines(work, by_file)
        lines += ['```', '']
    lines += ['(to-2023-risk-resilience-and-sustainability)=', '## Webinar series', '',
              '**2022 to 2023 — Risk, resilience and sustainability informed integrity management of infrastructure systems**', '',
              '[Open the fourteen-session series](webinars-2022-2023.md), with speaker details, poster versions, and supplementary reading. Direct session links are listed below.', '']
    for number, work in enumerate(sessions, 1):
        # Retain former entry fragments as useful links to the new activity page.
        lines += [f'{number}. <span id="{work["id"]}"></span> '
                  f"{work['date']} — {{ref}}`{work['title']} <{work['id']}>`", '']
    if any(work['group'] == 'education' and work['document_type'] == 'Course terms' for work in works):
        lines += ['## Course administration', '']
    for work in works:
        if work['group'] == 'education' and work['document_type'] == 'Course terms':
            lines += ['```{div} library-work library-secondary', f":name: {work['id']}", '', f"**{work['title']}** {permalink(work)}", '', 'Undated course terms, retained with the activity archive.', '']
            lines += resource_lines(work, by_file) + ['```', '']
    return '\n'.join(lines)


def catalogue_page(group, entries, works=None):
    """Render one entry per work or activity, with labelled source resources."""
    works = load_works() if works is None else works
    check_work_coverage(works, entries)
    if group == 'education':
        return education_page(entries, works)
    by_file = {entry['local_file']: entry for entry in entries}
    selected = [work for work in works if work['group'] == group]
    section_dates = {work['section']: work['section_order'] for work in selected}
    sections = sorted(section_dates, key=lambda section: (section_dates[section], section), reverse=True)
    if group == 'reports':
        sections = ['Risk assessment', 'Risk acceptance and LQI', 'Structural assessment',
                    'Monitoring and inspection', 'Governance and climate']
    lines = [f'# {TITLES[group]}', '', INTRODUCTIONS[group], '']
    for section in sections:
        if not any(work['section'] == section for work in selected):
            continue
        lines += [f'## {section}', '']
        if section == '2022 to 2023 — Risk, resilience and sustainability':
            lines += ['Webinar series: *Risk, resilience and sustainability informed integrity management of infrastructure systems*. Dates below identify the scheduled sessions.', '']
        records = sorted((work for work in selected if work['section'] == section),
                         key=lambda work: (work['date'], work['order'], work['title']))
        records.sort(key=lambda work: work.get('supporting', False))
        supporting_open = False
        for work in records:
            supporting = work.get('supporting', False)
            if supporting and not supporting_open:
                label = 'Other activity documents' if any(not item.get('supporting') for item in records) else 'Activity documents'
                lines += [f'### {label}', '', '::::::{div} library-supporting', '']
                supporting_open = True
            heading = '####' if supporting else '###'
            if supporting:
                lines += [':::::{div} library-work', '']
            lines += [f"({work['id']})=", '', f"{heading} {work['title']} {permalink(work)}", '']
            # The event heading supplies the common date; retain more precise dates.
            show_date = group != 'events' or work['date'] != work['section_order']
            lines += metadata_lines(work, show_date=show_date)
            lines += resource_lines(work, by_file)
            if supporting:
                lines += [':::::', '']
        if supporting_open:
            lines += ['::::::', '']
    return '\n'.join(lines)


def webinar_page(entries, works):
    by_file = {entry['local_file']: entry for entry in entries}
    sessions = sorted((work for work in works if work['page'] == 'catalogue/webinars-2022-2023'),
                      key=lambda work: work['date'])
    lines = ['# Risk, resilience and sustainability', '',
             '2022 to 2023 webinar series: *Risk, resilience and sustainability informed integrity management of infrastructure systems*. The fourteen sessions follow their scheduled sequence. Poster variants remain separately labelled, and supplementary reading is linked with its session.', '',
             'Dates identify the scheduled sessions. Posters preserve the original access details and do not provide recordings. Variant labels describe differences in content or layout without establishing which version came later.', '']
    for work in sessions:
        lines += [f"({work['id']})=", f"## {work['title']} {permalink(work)}", '']
        lines += metadata_lines(work)
        lines += resource_lines(work, by_file)
    return '\n'.join(lines)


def load_literature():
    return json.loads((ROOT / 'catalogue/literature.json').read_text(encoding='utf-8'))


def literature_page():
    """Keep externally hosted references separate from archived source files."""
    lines = ['# Special issues and papers', '',
             'Journal issues and selected papers associated with JCSS. Links lead to publisher or institutional records, where full-text access depends on the provider. Original JCSS reports and event documents remain available from their catalogue entries.', '']
    for publication in load_literature():
        is_paper = publication['type'] == 'Journal paper'
        heading = '###' if is_paper else '##'
        lines += [f"({publication['id']})=", '',
                  f"{heading} {publication['title']} {permalink(publication)}", '']
        citation = '. '.join(part.rstrip('.') for part in [
            publication['authors'], f"({publication['date']})",
            f"*{publication['journal']}*, {publication['volume']}", publication['location']
        ] if part)
        lines += [citation + '.', '']
        if publication.get('editors'):
            lines += ['Editors: ' + publication['editors'] + '.', '']
        if publication.get('description'):
            lines += [publication['description'], '']
        if publication['note']:
            lines += [publication['note'], '']
        links = [f"[Publisher {'paper' if is_paper else 'issue'}]({publication['publisher_url']})"]
        if publication['doi']:
            links.insert(0, f"[DOI: {publication['doi']}](https://doi.org/{publication['doi']})")
        if publication['evidence_url'] != publication['publisher_url']:
            links.append(f"[{publication['evidence_label']}]({publication['evidence_url']})")
        lines += [' · '.join(links), '']
    return '\n'.join(lines)


def page_outputs(entries, works):
    pages = {f'catalogue/{group}': catalogue_page(group, entries, works) for group in TITLES}
    pages['catalogue/webinars-2022-2023'] = webinar_page(entries, works)
    pages['catalogue/literature'] = literature_page()
    return pages


def prepare_originals(entries, archive):
    """Reuse converted sources; copy only originals missing from the repository."""
    register = {row['local_file']: row for row in csv.DictReader(
        (ROOT / 'catalogue/conversion-register.csv').open(encoding='utf-8-sig', newline=''))}
    expected = {name for name, row in register.items()
                if row['collection'] in ('publications', 'events', 'education', 'governance')}
    assert len(entries) == len({entry['local_file'] for entry in entries})
    assert {entry['local_file'] for entry in entries} == expected, 'Catalogue coverage differs from the register'
    for entry in entries:
        assert entry['sha256'] == register[entry['local_file']]['sha256']
        destination = ROOT / entry['original']
        if not destination.exists() and archive is not None:
            source = archive / entry['local_file']
            assert original_hash(source) == entry['sha256'], source
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        assert original_hash(destination) == entry['sha256'], destination
        if entry['reader']:
            assert (ROOT / entry['reader']).is_file(), entry['reader']
        if entry['conversion_archive']:
            assert not entry['reader'], 'A presentation must link to its original download'
            assert (ROOT / entry['conversion_archive']).is_file()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--release', action='store_true',
                        help='Verify the selected originals without the private conversion register')
    options = parser.parse_args()
    assert not (options.check and options.archive), 'Check mode must not copy files'
    entries = load_entries()
    if options.release:
        assert options.archive is None, 'Release mode must not import files'
        for entry in entries:
            if entry.get('external_original'):
                assert entry['original'] == entry['source_url'] and not entry['reader']
                continue
            assert original_hash(ROOT / entry['original']) == entry['sha256'], entry['original']
            if entry['reader']:
                assert (ROOT / entry['reader']).is_file(), entry['reader']
    else:
        prepare_originals(entries, options.archive)
    for page, expected in page_outputs(entries, load_works()).items():
        destination = ROOT / f'{page}.md'
        if options.check:
            assert destination.read_text(encoding='utf-8') == expected, destination
        else:
            destination.write_text(expected, encoding='utf-8')
    print(f'Catalogue: {len(load_works())} work/activity entries, {len(entries)} originals verified, '
          f'{len(load_literature())} external literature records.')


if __name__ == '__main__':
    main()
