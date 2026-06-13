.PHONY: test validate eval doctor all

test:
	python -m unittest discover -s tests -v

validate:
	python scripts/validate_data.py

eval:
	python scripts/run_evals.py

doctor:
	python scripts/doctor.py

all: doctor validate test eval
