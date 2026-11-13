# SE3002 Assignment 2 — Student Registration Module

This is the **system under test** for black-box and white-box testing, not a reference-correct solution.

## Files
- `registration.py`: Python application to test.
- `REQUIREMENTS.md`: authoritative functional requirements, status strings, and sample scenarios.
- `requirements.txt`: dependencies for test development.

## Getting started
```bash
python -m pip install -r requirements.txt
python -c "from registration import Student, Course, register_course; print(register_course(Student('S001'), Course('CS201', 3, 30)))"
```

## Suggested student workflow
1. Derive ECP/BVA/decision table tests from `REQUIREMENTS.md` **without using implementation behavior as the expected result**.
2. Create `tests/test_blackbox.py`, execute the cases, and log suspected defects as GitHub Issues.
3. Inspect the code and develop `tests/test_whitebox.py` to exercise decisions, branches, conditions, and basis paths.
4. Document CFG and manual MC/DC pairs for a selected function.
5. Record failing tests faithfully. Do not alter expected results to force tests to pass.
6. Make any defect fixes in a separate Pull Request with accompanying regression tests.

Some tests may fail against the supplied source. This is intentional for the exercise.

---

## Assignment 2 deliverables (testing)

```bash
python -m pip install -r requirements.txt
python -m pytest tests/test_blackbox.py -v
python -m pytest tests/ --cov=registration --cov-branch --cov-report=term-missing
```

| Path | Content |
|---|---|
| `tests/test_blackbox.py` | ECP, BVA, decision-table and state-change tests (IDs ECP-xx, BVA-xx, DT-xx, ST-xx) |
| `tests/test_whitebox.py` | Basis-path (WB-P01..P10), MC/DC (WB-MCDC-T1..T4) and coverage-gap tests (WB-G01..G04) |
| `docs/blackbox_test_design.xlsx` | ECP, BVA and consolidation sheets |
| `docs/decision_table.xlsx` | Decision table and priority combinations |
| `docs/cfg.png` | CFG of `registration_decision()` |
| `docs/testing_report.pdf` | Final report |
| `docs/*.txt` | Preserved pytest and coverage output from the unmodified source |

`registration.py` is intentionally unmodified on `main`; defect fixes live on the `defect-fixes` branch.
