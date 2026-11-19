"""Copy source mathematics used by inline HTML in static reading editions.

Sphinx copies Markdown image references itself. Inline mathematical source
crops use HTML to preserve their physical size and baseline, so their relative
asset directories must also be copied into the generated HTML tree.
"""
from pathlib import Path
import re
import shutil


def copy_inline_assets(app, exception):
    """Copy only PNG assets referenced by the publication's inline HTML."""
    if exception or app.builder.format != 'html':
        return
    source_root = Path(app.srcdir)
    for publication in (source_root / 'publications').iterdir():
        image_folder = publication / 'images'
        if not image_folder.is_dir():
            continue
        article_path = publication / 'index.md'
        if not article_path.is_file():
            continue
        article = article_path.read_text(encoding='utf-8')
        image_names = set(re.findall(r'src="images/([^"/]+\.png)"', article))
        for image_name in image_names:
            image_path = image_folder / image_name
            relative_path = image_path.relative_to(source_root)
            target = Path(app.outdir) / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image_path, target)


def omit_execution_scripts(app, pagename, templatename, context, doctree):
    """Keep this static library free of unused notebook execution bootstrap."""
    context['script_files'] = [script for script in context.get('script_files', [])
                               if 'sphinx-thebe.js' not in str(getattr(script, 'filename', script))
                               and 'THEBE_JS_URL' not in str(getattr(script, 'attributes', {}).get('body', ''))]


def setup(app):
    app.connect('build-finished', copy_inline_assets)
    app.connect('html-page-context', omit_execution_scripts)
    return {'version': '1.0', 'parallel_read_safe': True, 'parallel_write_safe': True}
