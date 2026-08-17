.PHONY: pipeline notebooks notebooks-build lint typecheck test all clean

pipeline:
	PYTHONPATH=src python scripts/run_pipeline.py

notebooks-build:
	python scripts/create_notebooks.py

notebooks:
	PYTHONPATH=src python scripts/run_notebooks.py

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
