.PHONY: pipeline notebooks notebooks-build pdf lint typecheck test all clean

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

lint:
	ruff check .

typecheck:
	mypy src

test:
	PYTHONPATH=src pytest

all: pipeline notebooks test

clean:
	rm -f data/interim/*.csv data/processed/*.csv
	rm -f outputs/tables/*.csv outputs/metrics/*.json outputs/figures/*.png
	rm -f report/report.tex
