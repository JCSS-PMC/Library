"""Keep retained conversion work outside reader navigation and search.

The archive still builds for the existing source-content checks and direct
private review links. Filtering discovery is not an access-control mechanism.
"""
from functools import lru_cache
import json
from pathlib import Path
import posixpath
from urllib.parse import urlsplit

from bs4 import BeautifulSoup


@lru_cache
def archived_documents(source_directory):
    entries = json.loads((Path(source_directory) / 'catalogue/entries.json').read_text(encoding='utf-8'))
    return {'catalogue/conversion-archive'} | {
        entry['conversion_archive'].removesuffix('.md')
        for entry in entries if entry['conversion_archive']
    }


def archive_target(current_page, href, archived):
    path = urlsplit(href).path
    if path:
        target = posixpath.normpath(posixpath.join(posixpath.dirname(current_page), path))
    else:
        target = current_page
    return target.removesuffix('.html') in archived


def filter_navigation(app, pagename, templatename, context, doctree):
    """Filter the theme's generated tree and previous/next discovery links."""
    archived = archived_documents(str(app.srcdir))
    generate_tree = context.get('generate_toctree_html')
    if generate_tree is not None:
        def reader_tree(*args, **kwargs):
            # Copy the theme's cached tree before filtering it.
            tree = BeautifulSoup(str(generate_tree(*args, **kwargs)), 'html.parser')
            for permalink in tree.select('.library-permalink'):
                permalink.decompose()
            for caption in tree.select('p.caption'):
                if caption.get_text(strip=True) == 'Private review':
                    siblings = caption.find_next_sibling('ul')
                    if siblings is not None:
                        siblings.decompose()
                    caption.decompose()
            for link in list(tree.select('a[href]')):
                if link.attrs is None:
                    continue
                if archive_target(pagename, link['href'], archived):
                    item = link.find_parent('li')
                    if item is not None:
                        item.decompose()
            return tree
        context['generate_toctree_html'] = reader_tree
    for direction in ('prev', 'next'):
        neighbour = context.get(direction)
        if neighbour and archive_target(pagename, neighbour['link'], archived):
            context[direction] = None


def filter_search(app):
    """Prune archive records after document indexing and before index output."""
    indexer = getattr(app.builder, 'indexer', None)
    if indexer is not None:
        indexer.prune(set(app.env.all_docs) - archived_documents(str(app.srcdir)))
    return []


@lru_cache
def catalogue_data(source_directory):
    root = Path(source_directory)
    entries = json.loads((root / 'catalogue/entries.json').read_text(encoding='utf-8'))
    works = json.loads((root / 'catalogue/works.json').read_text(encoding='utf-8'))
    workshops = json.loads((root / 'catalogue/workshops.json').read_text(encoding='utf-8'))
    return entries, works, workshops


def enrich_page(app, pagename, templatename, context, doctree):
    """Add catalogue return paths and descriptive download filenames."""
    # Distinguish printing the rendered page from downloading the source PDF.
    for group in context.get('header_buttons', []):
        if group.get('label') == 'download-buttons':
            for button in group['buttons']:
                if button.get('label') == 'download-pdf-button':
                    button['text'] = 'Print this page'
                elif button.get('label') == 'download-source-button':
                    button['text'] = 'Markdown source'
    # Heading content is copied into the page TOC. Remove its permanent links
    # there to prevent nested anchors and duplicate navigation controls.
    generate_contents = context.get('generate_toc_html')
    if generate_contents and pagename.startswith('catalogue/'):
        def contents_tree(*args, **kwargs):
            # The theme may already have cached its generated TOC. Clean a copy
            # of that output rather than changing the input after caching.
            contents = BeautifulSoup(str(generate_contents(*args, **kwargs)), 'html.parser')
            for permalink in contents.select('.library-permalink'):
                permalink.decompose()
            return contents
        context['generate_toc_html'] = contents_tree
    entries, works, workshops = catalogue_data(str(app.srcdir))
    groups = {'reports': 'Reports and guidance', 'events': 'Workshop archive',
              'education': 'Education', 'notices': 'Notices'}
    by_file = {entry['local_file']: entry for entry in entries}
    reader_work = None
    reader_entry = None
    for work in works:
        for resource in work['resources']:
            reader = by_file[resource['file']]['reader']
            if reader and pagename.startswith(reader.removesuffix('/index.md') + '/'):
                reader_work = work
                reader_entry = by_file[resource['file']]
                break
        if reader_work:
            break

    def relative(page):
        return app.builder.get_relative_uri(pagename, page)

    breadcrumbs = [{'label': 'Library', 'href': relative('intro')}]
    if reader_work:
        group = reader_work['group']
        breadcrumbs.append({'label': groups[group], 'href': relative('catalogue/' + group)})
        if reader_work['page'] != 'catalogue/' + group:
            breadcrumbs.append({'label': 'Webinar series', 'href': relative(reader_work['page'])})
        breadcrumbs.append({'label': 'Reading edition', 'href': ''})
        label = 'Back to webinar session' if reader_work['page'].endswith('webinars-2022-2023') else 'Back to catalogue entry'
        context['library_return'] = {'label': label, 'href': relative(reader_work['page']) + '#' + reader_work['id']}
        if group == 'events':
            workshop_id = reader_work['section']
            context['library_return'] = {'label': workshops[workshop_id]['heading'],
                                         'href': relative('catalogue/events') + '#' + workshop_id}
    elif pagename == 'catalogue/webinars-2022-2023':
        breadcrumbs += [{'label': 'Education', 'href': relative('catalogue/education')},
                        {'label': 'Webinar series', 'href': ''}]
        context['library_return'] = {'label': 'Back to Education', 'href': relative('catalogue/education') + '#webinar-series'}
    elif pagename == 'catalogue/literature':
        breadcrumbs.append({'label': 'Special issues and papers', 'href': ''})
    elif pagename in {'catalogue/' + group for group in groups}:
        breadcrumbs.append({'label': groups[pagename.split('/')[1]], 'href': ''})
    else:
        breadcrumbs = []
    context['library_breadcrumbs'] = breadcrumbs

    # Sphinx retains its hashed asset destinations. The download attribute gives
    # users the descriptive archive filename, including for generic source.pdf.
    download_names = {}
    for entry in entries:
        destination = app.env.dlfiles.get(entry['original'])
        if destination:
            download_names['_downloads/' + destination[1]] = entry
    if reader_entry:
        destination = app.env.dlfiles[reader_entry['original']][1]
        context['library_original'] = {
            'href': posixpath.relpath('_downloads/' + destination, posixpath.dirname(pagename)),
            'filename': Path(reader_entry['local_file']).name,
            'title': reader_entry['title'],
        }
    if context.get('body'):
        body = BeautifulSoup(context['body'], 'html.parser')
        # Earlier abstract footers linked to retained slide conversions. Follow
        # the selected presentation format while leaving the source body intact.
        archived_sources = {
            entry['conversion_archive'].removesuffix('.md'): entry
            for entry in entries if entry['conversion_archive']
        }
        for link in body.select('a[href]'):
            target = posixpath.normpath(posixpath.join(posixpath.dirname(pagename), urlsplit(link['href']).path))
            entry = archived_sources.get(target.removesuffix('.html'))
            if entry and link.get_text().startswith('Related presentation:'):
                destination = '_downloads/' + app.env.dlfiles[entry['original']][1]
                link['href'] = posixpath.relpath(destination, posixpath.dirname(pagename))
                link['class'] = ['reference', 'download']
                link.append(' (original PDF)')
        for link in body.select('a.reference.download[href]'):
            target = posixpath.normpath(posixpath.join(posixpath.dirname(pagename), urlsplit(link['href']).path))
            entry = download_names.get(target)
            if entry:
                link['download'] = Path(entry['local_file']).name
                link['aria-label'] = f"{link.get_text(' ', strip=True)}: {entry['title']}"
        context['body'] = str(body)

    # Include download-only course groups beside the series in the active sidebar.
    if pagename in {'catalogue/education', 'catalogue/webinars-2022-2023'} or (reader_work and reader_work['group'] == 'education'):
        generate_tree = context.get('generate_toctree_html')
        if generate_tree:
            def education_tree(*args, **kwargs):
                tree = generate_tree(*args, **kwargs)
                for link in tree.select('a[href]'):
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(pagename), urlsplit(link['href']).path)) if urlsplit(link['href']).path else pagename
                    if target.removesuffix('.html') != 'catalogue/education':
                        continue
                    children = link.find_parent('li').find('ul')
                    if children is not None:
                        sections = [('Courses', 'courses', 'first')]
                        if any(work['document_type'] == 'Course terms' for work in works):
                            sections.append(('Course administration', 'course-administration', 'last'))
                        for label, anchor, position in sections:
                            item = tree.new_tag('li', attrs={'class': 'toctree-l2'})
                            child_link = tree.new_tag('a', href=relative('catalogue/education') + '#' + anchor, attrs={'class': 'reference internal'})
                            child_link.string = label
                            item.append(child_link)
                            if position == 'first':
                                children.insert(0, item)
                            else:
                                children.append(item)
                    break
                return tree
            context['generate_toctree_html'] = education_tree


def write_catalogue_search(app, exception):
    """Emit a static work index; retain the independent full-text index."""
    if exception is not None or app.builder.format != 'html':
        return
    entries, works, workshops = catalogue_data(str(app.srcdir))
    by_file = {entry['local_file']: entry for entry in entries}
    records = []
    for work in works:
        authors = work['authors'] or work.get('organisation', '')
        workshop = workshops.get(work['section'], {})
        activity = workshop.get('heading', work['section'])
        editors = work.get('editors', '')
        resources = [resource['label'].removeprefix('Download ') for resource in work['resources']]
        formats = sorted({Path(by_file[resource['file']]['original']).suffix[1:].upper() for resource in work['resources']})
        records.append({'id': work['id'], 'title': work['title'], 'date': work['date'],
                        'authors': authors, 'editors': editors, 'status': work.get('status', ''),
                        'date_kind': work['date_kind'], 'type': work['document_type'], 'activity': activity,
                        'formats': formats, 'file_count': len(resources),
                        'has_reader': any(by_file[resource['file']]['reader'] for resource in work['resources']),
                        'resources': resources, 'href': work['page'] + '.html#' + work['id'],
                        'search_text': ' '.join([work['title'], authors, editors, work.get('organisation', ''),
                                                work.get('status', ''), work['date'], work['document_type'],
                                                activity, workshop.get('topic', ''), work.get('note', ''), *resources, *formats])})
    target = Path(app.outdir) / '_static/library-search-index.json'
    literature = json.loads((Path(app.srcdir) / 'catalogue/literature.json').read_text(encoding='utf-8'))
    for publication in literature:
        records.append({
            'id': publication['id'], 'title': publication['title'], 'date': publication['date'],
            'authors': publication['authors'], 'editors': publication.get('editors', ''),
            'status': '', 'date_kind': 'Publication', 'type': publication['type'],
            'activity': publication['journal'], 'external': True,
            'formats': [], 'file_count': 0, 'has_reader': False, 'resources': [],
            'href': 'catalogue/literature.html#' + publication['id'],
            'search_text': ' '.join(str(value) for value in publication.values()),
        })
    target.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')


def setup(app):
    # The theme installs generate_toctree_html at the default priority of 500.
    app.connect('html-page-context', filter_navigation, priority=900)
    app.connect('html-page-context', enrich_page, priority=950)
    app.connect('html-collect-pages', filter_search)
    app.connect('build-finished', write_catalogue_search)
    return {'version': '1.0', 'parallel_read_safe': True, 'parallel_write_safe': True}
