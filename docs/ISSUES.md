# Defect log (copy each block into a GitHub Issue)

Evidence: docs/blackbox_initial_run.txt (unmodified source). Status of all: Open until PR "defect-fixes" merges.

## DEF-01  check_credit_limit rejects a total of exactly 18 credits
- Requirement: FR-01 (also FR-07)
- Steps: `check_credit_limit(15, 3)`
- Expected: `True` (15 + 3 = 18 allowed)  |  Actual: `False`
- Failed tests: test_check_credit_limit[BVA-08], [BVA-10], [BVA-12]; test_registration_decision[BVA-30], [BVA-34]
- Cause: `registration.py` line 34 uses `<` instead of `<=`

## DEF-02  prerequisites_satisfied accepts a student with only some prerequisites
- Requirement: FR-03 (also FR-06)
- Steps: `prerequisites_satisfied({"CS101"}, {"CS101","MATH101"})`
- Expected: `False`  |  Actual: `True`
- Failed tests: test_prerequisites_satisfied[ECP-32+BVA-41]; test_registration_decision[ECP-16]
- Cause: line 41 uses `bool(completed.intersection(required))` (any) instead of subset (all)

## DEF-03  Dues of Rs. 1 to Rs. 1000 do not block registration
- Requirement: FR-04 (also FR-09)
- Steps: `registration_decision(Student("S001", outstanding_dues=1), Course("CS201", 3, 30))`
- Expected: `DUES_BLOCK`  |  Actual: `REGISTERED`
- Failed tests: [ECP-10+DT-01], [BVA-21], [DT-07], [DT-11], [DT-13], test_unsuccessful_registration_changes_nothing[ST05-dues], [ST05-dues-full]
- Cause: line 50 uses `dues > 1000` instead of `dues > 0`

## DEF-04  Full course is never WAITLISTED (dead code)
- Requirement: FR-08, FR-12
- Steps: `registration_decision(Student("S001"), Course("CS201", 3, 30, enrolled=30))`
- Expected: `WAITLISTED`  |  Actual: `REGISTERED`
- Failed tests: [ECP-19+BVA-24+DT-05], [BVA-28], test_ST03, test_ST04 (also WB-P09, WB-G01, WB-G02)
- Cause: line 58 uses `enrolled > capacity`; validation guarantees `enrolled <= capacity`, so lines 59 and 71 are unreachable

## DEF-05  withdraw_course does not decrement course enrollment
- Requirement: FR-13 (SRS scenario 6)
- Steps: register-enrolled student with `Course(..., enrolled=10)`, call `withdraw_course`
- Expected: `course.enrolled == 9`  |  Actual: `10`
- Failed tests: test_ST11, test_ST13, test_ST14 (also WB-G04)
- Cause: missing `course.enrolled -= 1` in `withdraw_course`
