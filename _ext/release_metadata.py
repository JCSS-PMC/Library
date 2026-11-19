"""Generate discovery metadata for the selected public book only."""
from pathlib import Path
from xml.etree import ElementTree
from html import escape


def describe_page(app, pagename, templatename, context, doctree):
    title = context.get('title', 'JCSS Library')
    description = title + '. JCSS reports, source documents, and publication information.'
    context['metatags'] = context.get('metatags', '') + '<meta name="description" content="' + escape(description, quote=True) + '" />'


def write_discovery_files(app, exception):
    if exception is not None or app.builder.format != 'html':
        return
    root = Path(app.outdir)
    base_url = app.config.html_baseurl.rstrip('/') + '/'
    namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    ElementTree.register_namespace('', namespace)
    sitemap = ElementTree.Element(f'{{{namespace}}}urlset')
    for page in sorted(app.env.found_docs):
        url = ElementTree.SubElement(sitemap, f'{{{namespace}}}url')
        ElementTree.SubElement(url, f'{{{namespace}}}loc').text = base_url + page + '.html'
    ElementTree.ElementTree(sitemap).write(root / 'sitemap.xml', encoding='utf-8', xml_declaration=True)
    (root / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: ' + base_url + 'sitemap.xml\n', encoding='utf-8')
    (root / '.nojekyll').touch()
    # Preserve the preview's former About address without a second content page.
    (root / 'about.html').write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta http-equiv="refresh" content="0; url=intro.html#about-the-library">'
        '<link rel="canonical" href="' + base_url + 'intro.html#about-the-library">'
        '<title>About the Library</title></head><body>'
        '<a href="intro.html#about-the-library">About the Library</a>'
        '<script>location.replace("intro.html"+(location.hash||"#about-the-library"));</script>'
        '</body></html>', encoding='utf-8')


def setup(app):
    app.connect('html-page-context', describe_page)
    app.connect('build-finished', write_discovery_files)
    return {'version': '1.0', 'parallel_read_safe': True, 'parallel_write_safe': True}
