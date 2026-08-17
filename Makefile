.PHONY: pipeline notebooks test all clean

pipeline:
	PYTHONPATH=src python scripts/run_pipeline.py

notebooks:
	PYTHONPATH=src python scripts/run_notebooks.py

test:
	PYTHONPATH=src pytest

all: pipeline notebooks test

clean:
	rm -f data/interim/*.csv data/processed/*.csv
	rm -f outputs/tables/*.csv outputs/metrics/*.json outputs/figures/*.png
	rm -f report/report.tex
