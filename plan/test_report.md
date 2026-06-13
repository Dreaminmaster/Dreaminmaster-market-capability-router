# Test Report

Run locally with:

```bash
pip install -e .
make all
```

Expected checks:

- environment doctor;
- seed-data validation;
- unit tests;
- product-level evaluation suite with at least 90% pass rate.

The release package should not be marked ready if critical risk cases fail.
