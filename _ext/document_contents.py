"""Show a publication's complete outline in the PMC theme's secondary sidebar.

Multi-page publications use an index and its ordered children in _toc.yml.
Read Sphinx's heading trees at build time so there is no duplicate outline to
maintain and no client-side request needed to populate the navigation.
"""

from html import escape

from docutils import nodes


def publication_pages(environment, root):
    """Return the publication's pages in their configured reading order."""
    pages = [root]
    for child in environment.toctree_includes.get(root, []):
        pages.extend(publication_pages(environment, child))
    return pages


def render_heading_list(builder, current_page, document_page, heading_list):
    """Render relative links while retaining the source heading hierarchy."""
    entries = []
    for item in heading_list.children:
        if not isinstance(item, nodes.list_item):
            continue
        reference = next(item.findall(nodes.reference), None)
        if reference is None:
            continue

        anchor = reference.get('anchorname', '')
        destination = builder.get_relative_uri(current_page, document_page)
        href = destination + anchor or '#'
        is_current_page = document_page == current_page and not anchor
        current_attributes = (
            ' class="document-current-page" aria-current="page"'
            if is_current_page else ''
        )
        link = (
            f'<a href="{escape(href, quote=True)}"{current_attributes}>'
            f'{escape(reference.astext())}</a>'
        )
        children = ''.join(
            '<ul>' + render_heading_list(builder, current_page, document_page, child) + '</ul>'
            for child in item.children if isinstance(child, nodes.bullet_list)
        )
        entries.append(f'<li>{link}{children}</li>')
    return ''.join(entries)


def show_document_contents(app, pagename, templatename, context, doctree):
    """Expose the full outline for single-page and multi-page publications."""
    if not pagename.startswith('publications/'):
        return
    # A single-page publication already contains the entire document. Expose
    # its complete heading hierarchy too, including the deeper source sections.
    context['theme_show_toc_level'] = 6
    context['theme_toc_title'] = 'Document contents'
    publication_directory = pagename.split('/')[:2]
    root = '/'.join(publication_directory) + '/index'
    if not app.env.toctree_includes.get(root):
        return

    outline = ''.join(
        render_heading_list(app.builder, pagename, page, app.env.tocs[page])
        for page in publication_pages(app.env, root)
    )
    # The theme applies its normal typography, mobile drawer and scroll tracking
    # to this outline. Expand every heading level present in the document.
    context['toc'] = f'<ul class="document-contents">{outline}</ul>'


def setup(app):
    # Populate the outline before the theme caches it and hides empty sidebars.
    app.connect('html-page-context', show_document_contents, priority=400)
    return {'version': '1.0', 'parallel_read_safe': True, 'parallel_write_safe': True}
