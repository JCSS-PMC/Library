# JCSS Library

Reports, guidance, event contributions, and educational material associated with the Joint Committee on Structural Safety. Online reading editions follow the PMC Jupyter Book layout and retain their source wording, notation, figures, and references. Presentations remain available as original downloads.

1. [Read the Library](https://jcss-pmc.github.io/Library/intro.html)
2. [JCSS website](https://www.jcss-lc.org/)
3. [Probabilistic Model Code](https://jcss-pmc.github.io/PMC/part-00/intro.html)

The [opening page](intro.md#about-the-library) explains source editions, citation examples, corrections, and attribution. Catalogue dates and qualifications remain part of the source record. Inclusion does not turn an archived draft into current approved guidance.

## Build locally

Use Python 3.12 and install `requirements-release.txt` in a virtual environment. The release requirements record the environment used to validate this edition. Build the static book with:

```sh
python catalogue/build_catalogue.py --release --check
jupyter-book build . --all --warningiserror --keep-going
python -m http.server 8765 --directory _build/html --bind 127.0.0.1
```

Open `http://127.0.0.1:8765/intro.html`. Notebook execution is disabled. To regenerate catalogue pages after a metadata correction, run `python catalogue/build_catalogue.py --release` before rebuilding.

## Sources and contributions

`catalogue/entries.json` records each original file, source URL, and SHA-256 checksum. `catalogue/works.json` supplies the publication and activity groupings. External journal references are maintained separately in `catalogue/literature.json`.

Keep original files unchanged and preserve document URLs when making corrections. Report issues with the document title, source edition, location, and expected correction. Substantive scientific corrections require an identified erratum or replacement rather than a silent change to the historical text.

Authorship and rights remain with the respective works. This repository does not apply a blanket licence to source documents or JCSS artwork.
