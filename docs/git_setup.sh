#!/usr/bin/env bash
# Run once per team. Each member commits their own work from their own account.
set -e
git init -b main
git add registration.py requirements.txt README.md REQUIREMENTS.md Student_Registration_SRS.docx
git commit -m "Add starter code, SRS and requirements"
git checkout -b blackbox-testing
git add tests/test_blackbox.py docs/blackbox_test_design.xlsx docs/decision_table.xlsx docs/blackbox_initial_run.txt docs/ISSUES.md
git commit -m "Add black-box ECP, BVA, decision-table and state tests with design sheets"
git add .github/workflows/tests.yml
git commit -m "Add GitHub Actions workflow running pytest with coverage"
git checkout main && git checkout -b whitebox-testing
git add tests/test_whitebox.py docs/cfg.png docs/coverage_initial.txt docs/coverage_final_before_fix.txt docs/all_tests_before_fix.txt
git commit -m "Add white-box basis-path, MC/DC and coverage-gap tests with CFG"
# After the failing Actions run and issues are recorded:
git checkout main && git checkout -b defect-fixes
git apply docs/defect-fixes.patch
git add registration.py docs/coverage_after_fix.txt docs/testing_report.pdf docs/defect-fixes.patch
git commit -m "Fix DEF-01..DEF-05 (closes #1 #2 #3 #4 #5)"
# git remote add origin <url>; git push -u origin --all
