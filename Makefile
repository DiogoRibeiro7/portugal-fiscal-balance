.PHONY: pipeline notebooks notebooks-build pdf paper docs docs-check lint typecheck test all clean

pipeline:
	PYTHONPATH=src python scripts/run_pipeline.py

notebooks-build:
	python scripts/create_notebooks.py

notebooks:
	PYTHONPATH=src python scripts/run_notebooks.py

# Requires a LaTeX installation. report/report.pdf is committed, so run this after
# changing anything the report reads and commit the rebuilt PDF with the change.
pdf:
	cd report && latexmk -pdf -interaction=nonstopmode report.tex

# The manuscript. Needs paper/generated/, which `make pipeline` writes, and runs
# bibtex for the bibliography. paper/paper.pdf is committed like report.pdf.
paper:
	cd paper && latexmk -pdf -interaction=nonstopmode paper.tex

lint:
	ruff check .

typecheck:
	mypy src

test:
	PYTHONPATH=src pytest

# Both documents, then the check that CI used to run remotely. It hashes the
# committed PDFs, rebuilds both from scratch with -g, and fails if either hash
# moved. That is what keeps the pdfTeX metadata suppression working: without it,
# every rebuild would produce a different file and the committed PDFs would be
# meaningless as reproducible outputs.
#
# This lives here rather than in CI because CI paid for it with a full texlive
# install on every push, which hung and kept the pipeline red for nineteen
# commits. Locally it costs two compiles you were going to run anyway.
docs: pdf paper

docs-check:
	@for doc in report paper; do \
		sha256sum "$$doc/$$doc.pdf" > "/tmp/$$doc.sha"; \
	done
	cd report && latexmk -pdf -interaction=nonstopmode -halt-on-error -g report.tex
	cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error -g paper.tex
	@status=0; \
	for doc in report paper; do \
		if ! sha256sum -c "/tmp/$$doc.sha" --quiet; then \
			echo "$$doc.pdf is not reproducible: a rebuild from identical inputs differs."; \
			echo "Check that the preamble still suppresses pdfTeX metadata."; \
			status=1; \
		fi; \
	done; \
	if [ $$status -eq 0 ]; then echo "Both PDFs are byte-identical on rebuild."; fi; \
	exit $$status

all: pipeline notebooks test

clean:
	rm -f data/interim/*.csv data/processed/*.csv
	rm -f outputs/tables/*.csv outputs/metrics/*.json outputs/figures/*.png
	rm -f report/report.tex
