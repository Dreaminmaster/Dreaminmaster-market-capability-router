.PHONY: test validate eval hybrid-eval doctor openminis-smoke all

test:
	python -m unittest discover -s tests -v

validate:
	python scripts/validate_data.py

eval:
	python scripts/run_evals.py

hybrid-eval:
	python scripts/run_hybrid_evals.py

doctor:
	python scripts/doctor.py

openminis-smoke:
	python scripts/openminis_smoke.py --skill-root "$${MCR_SKILL_ROOT:-skills}"

all: doctor validate test eval hybrid-eval
