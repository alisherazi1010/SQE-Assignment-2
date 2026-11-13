"""Black-box tests for the Student Course Registration System.

Expected results are derived from REQUIREMENTS.md only (FR-01 .. FR-15).
Test IDs: ECP-xx, BVA-xx, DT-xx (technique cases), ST-xx (state-change tests).
Cases that are exact duplicates across techniques are merged into one execution
with a combined ID (e.g. "ECP-19+BVA-24+DT-05") so traceability is preserved.
"""
import copy

import pytest

from registration import (
    Student,
    Course,
    check_credit_limit,
    prerequisites_satisfied,
    registration_decision,
    register_course,
    withdraw_course,
)

RAISES = "raises"
TECH_ORDER = {"ECP": 0, "BVA": 1, "DT": 2}


def make_student(**kw):
    kw.setdefault("student_id", "S001")
    return Student(**copy.deepcopy(kw))


def make_course(**kw):
    kw.setdefault("code", "CS201")
    kw.setdefault("credit_hours", 3)
    kw.setdefault("capacity", 30)
    return Course(**copy.deepcopy(kw))


def _norm(value):
    if isinstance(value, dict):
        return tuple(sorted((k, _norm(v)) for k, v in value.items()))
    if isinstance(value, (set, frozenset)):
        return tuple(sorted(value))
    if isinstance(value, (list, tuple)):
        return tuple(_norm(v) for v in value)
    return value


def _canon_decision(inputs):
    """Fill in defaults so {'capacity': 0} and {'capacity': 0, 'enrolled': 0} compare equal."""
    from dataclasses import asdict
    student_kw, course_kw = inputs
    return _norm(asdict(make_student(**student_kw))), _norm(asdict(make_course(**course_kw)))


def consolidate(cases, canon=_norm):
    """Merge exact duplicates (same inputs AND same expected result).

    case = (test_id, requirement, inputs, expected). Returns a list of
    pytest.param with combined ids and a combined requirement string.
    Different inputs with the same output are NOT duplicates.
    """
    merged = {}
    for test_id, req, inputs, expected in cases:
        key = (canon(inputs), _norm(expected))
        if key not in merged:
            merged[key] = [[test_id], {req}, inputs, expected]
        else:
            merged[key][0].append(test_id)
            merged[key][1].add(req)
    params = []
    for ids, reqs, inputs, expected in merged.values():
        ids.sort(key=lambda i: (TECH_ORDER[i.split("-")[0]], i))
        params.append(pytest.param(inputs, expected, id="+".join(ids)))
    return params


# --------------------------------------------------------------------------
# check_credit_limit  (FR-01, FR-02)   inputs = (current, new)
# --------------------------------------------------------------------------
CUR = "Invalid current credits"
CRS = "Invalid course credits"

CREDIT_CASES = [
    # ECP
    ("ECP-01", "FR-01", (10, 3), True),          # valid, within limit
    ("ECP-02", "FR-01", (16, 3), False),         # valid, exceeds limit
    ("ECP-03", "FR-02", (-5, 2), (RAISES, CUR)), # current below range
    ("ECP-04", "FR-02", (25, 2), (RAISES, CUR)), # current above range
    ("ECP-05", "FR-02", (5, 0), (RAISES, CRS)),  # course credits below range
    ("ECP-06", "FR-02", (5, 7), (RAISES, CRS)),  # course credits above range
    ("ECP-07", "FR-02", (-1, 9), (RAISES, CUR)), # both invalid: current first
    # BVA
    ("BVA-01", "FR-01", (0, 1), True),           # current min, course min
    ("BVA-02", "FR-02", (-1, 1), (RAISES, CUR)), # just below current min
    ("BVA-03", "FR-01", (18, 1), False),         # current max, any credit exceeds
    ("BVA-04", "FR-02", (19, 1), (RAISES, CUR)), # just above current max
    ("BVA-05", "FR-02", (5, 0), (RAISES, CRS)),  # just below course min
    ("BVA-06", "FR-02", (5, 5), (RAISES, CRS)),  # just above course max
    ("BVA-07", "FR-01", (5, 4), True),           # course max
    ("BVA-08", "FR-01", (14, 4), True),          # total exactly 18
    ("BVA-09", "FR-01", (15, 4), False),         # total 19
    ("BVA-10", "FR-01", (15, 3), True),          # total exactly 18 (SRS scenario 1)
    ("BVA-11", "FR-01", (16, 3), False),         # total 19 (SRS scenario 2)
    ("BVA-12", "FR-01", (17, 1), True),          # total exactly 18
    ("BVA-13", "FR-01", (17, 2), False),         # total 19
]


@pytest.mark.parametrize("inputs,expected", consolidate(CREDIT_CASES))
def test_check_credit_limit(inputs, expected):
    if isinstance(expected, tuple) and expected[0] == RAISES:
        with pytest.raises(ValueError, match=f"^{expected[1]}$"):
            check_credit_limit(*inputs)
    else:
        assert check_credit_limit(*inputs) is expected


# --------------------------------------------------------------------------
# prerequisites_satisfied  (FR-03)   inputs = (completed, required)
# --------------------------------------------------------------------------
PREREQ_CASES = [
    ("ECP-30", "FR-03", (set(), set()), True),                       # none required
    ("ECP-31", "FR-03", ({"CS101", "MATH101"}, {"CS101", "MATH101"}), True),
    ("ECP-32", "FR-03", ({"CS101"}, {"CS101", "MATH101"}), False),   # some missing
    ("ECP-33", "FR-03", (set(), {"CS101"}), False),                  # none completed
    ("ECP-34", "FR-03", ({"CS101", "MATH101", "PHY101"}, {"CS101"}), True),  # extras ok
    ("BVA-40", "FR-03", ({"CS101"}, {"CS101"}), True),               # exactly one required
    ("BVA-41", "FR-03", ({"CS101"}, {"CS101", "MATH101"}), False),   # one short of all
    ("BVA-42", "FR-03", ({"CS101", "MATH101"}, {"CS101", "MATH101"}), True),
]


@pytest.mark.parametrize("inputs,expected", consolidate(PREREQ_CASES))
def test_prerequisites_satisfied(inputs, expected):
    assert prerequisites_satisfied(*inputs) is expected


# --------------------------------------------------------------------------
# registration_decision  (FR-04..FR-10, FR-15)   inputs = (student_kw, course_kw)
# --------------------------------------------------------------------------
INV_DUES = "Invalid dues"
INV_CAP = "Invalid capacity or enrollment"

ALREADY = {"registered_courses": {"CS201"}}
PREQ = {"prerequisites": {"CS101"}}
OVER = {"current_credits": 16}  # 16 + 3 = 19 > 18
FULL = {"enrolled": 30}

DECISION_CASES = [
    # ---- ECP ----
    ("ECP-10", "FR-04", ({"outstanding_dues": 500}, {}), "DUES_BLOCK"),
    ("ECP-11", "FR-04", ({}, {}), "REGISTERED"),                      # dues zero
    ("ECP-12", "FR-15", ({"outstanding_dues": -100}, {}), (RAISES, INV_DUES)),
    ("ECP-13", "FR-05", (ALREADY, {}), "ALREADY_REGISTERED"),
    ("ECP-14", "FR-06", ({}, {}), "REGISTERED"),                      # no prerequisites
    ("ECP-15", "FR-06", ({"completed_courses": {"CS101", "MATH101"}},
                         {"prerequisites": {"CS101", "MATH101"}}), "REGISTERED"),
    ("ECP-16", "FR-06", ({"completed_courses": {"CS101"}},
                         {"prerequisites": {"CS101", "MATH101"}}), "PREREQUISITES_MISSING"),
    ("ECP-17", "FR-06", ({}, PREQ), "PREREQUISITES_MISSING"),         # none completed
    ("ECP-18", "FR-08", ({}, {"enrolled": 10}), "REGISTERED"),        # seats available
    ("ECP-19", "FR-08", ({}, FULL), "WAITLISTED"),                    # course full
    ("ECP-20", "FR-15", ({}, {"capacity": 0}), (RAISES, INV_CAP)),
    ("ECP-21", "FR-15", ({}, {"enrolled": 31}), (RAISES, INV_CAP)),
    ("ECP-22", "FR-15", ({}, {"enrolled": -1}), (RAISES, INV_CAP)),
    ("ECP-23", "FR-07", (OVER, {}), "CREDIT_LIMIT"),
    ("ECP-24", "FR-15", ({"outstanding_dues": -1}, {"capacity": 0}), (RAISES, INV_DUES)),  # dues validated first
    # ---- BVA ----
    ("BVA-20", "FR-04", ({"outstanding_dues": 0}, {}), "REGISTERED"),
    ("BVA-21", "FR-04", ({"outstanding_dues": 1}, {}), "DUES_BLOCK"),
    ("BVA-22", "FR-15", ({"outstanding_dues": -1}, {}), (RAISES, INV_DUES)),
    ("BVA-23", "FR-08", ({}, {"enrolled": 29}), "REGISTERED"),        # capacity - 1
    ("BVA-24", "FR-08", ({}, FULL), "WAITLISTED"),                    # == capacity
    ("BVA-25", "FR-15", ({}, {"enrolled": 31}), (RAISES, INV_CAP)),   # capacity + 1
    ("BVA-26", "FR-15", ({}, {"enrolled": -1}), (RAISES, INV_CAP)),   # below 0
    ("BVA-27", "FR-08", ({}, {"capacity": 1, "enrolled": 0}), "REGISTERED"),
    ("BVA-28", "FR-08", ({}, {"capacity": 1, "enrolled": 1}), "WAITLISTED"),
    ("BVA-29", "FR-15", ({}, {"capacity": 0, "enrolled": 0}), (RAISES, INV_CAP)),
    ("BVA-30", "FR-07", ({"current_credits": 15}, {"credit_hours": 3}), "REGISTERED"),  # total 18
    ("BVA-31", "FR-07", (OVER, {"credit_hours": 3}), "CREDIT_LIMIT"),                  # total 19
    ("BVA-32", "FR-07", ({"current_credits": 18}, {"credit_hours": 1}), "CREDIT_LIMIT"),
    ("BVA-33", "FR-07", ({"current_credits": 0}, {"credit_hours": 1}), "REGISTERED"),
    ("BVA-34", "FR-07", ({"current_credits": 14}, {"credit_hours": 4}), "REGISTERED"),  # total 18
    ("BVA-35", "FR-07", ({"current_credits": 15}, {"credit_hours": 4}), "CREDIT_LIMIT"),
    ("BVA-36", "FR-07", ({"current_credits": 0}, {"credit_hours": 4}), "REGISTERED"),
    # ---- Decision table: single condition true (D,A,P,L,S) ----
    ("DT-01", "FR-04", ({"outstanding_dues": 500}, {}), "DUES_BLOCK"),
    ("DT-02", "FR-05", (ALREADY, {}), "ALREADY_REGISTERED"),
    ("DT-03", "FR-06", ({}, PREQ), "PREREQUISITES_MISSING"),
    ("DT-04", "FR-07", (OVER, {}), "CREDIT_LIMIT"),
    ("DT-05", "FR-08", ({}, FULL), "WAITLISTED"),
    ("DT-06", "FR-08", ({}, {}), "REGISTERED"),                       # all false
    # ---- Decision table: priority combinations (FR-09) ----
    ("DT-07", "FR-09", ({"outstanding_dues": 500, **ALREADY, **OVER}, {**PREQ, **FULL}), "DUES_BLOCK"),   # D+A+P+L+S
    ("DT-08", "FR-09", ({**ALREADY, **OVER}, {**PREQ, **FULL}), "ALREADY_REGISTERED"),                    # A+P+L+S
    ("DT-09", "FR-09", (OVER, {**PREQ, **FULL}), "PREREQUISITES_MISSING"),                                # P+L+S
    ("DT-10", "FR-09", (OVER, FULL), "CREDIT_LIMIT"),                                                     # L+S
    ("DT-11", "FR-09", ({"outstanding_dues": 500}, FULL), "DUES_BLOCK"),                                  # D+S
    ("DT-12", "FR-09", ({**ALREADY}, PREQ), "ALREADY_REGISTERED"),                                        # A+P
    ("DT-13", "FR-09", ({"outstanding_dues": 500, **ALREADY}, {}), "DUES_BLOCK"),                         # D+A
    ("DT-14", "FR-09", ({**ALREADY, **OVER}, {}), "ALREADY_REGISTERED"),                                  # A+L
    ("DT-15", "FR-09", (OVER, PREQ), "PREREQUISITES_MISSING"),                                            # P+L
]


@pytest.mark.parametrize("inputs,expected", consolidate(DECISION_CASES, _canon_decision))
def test_registration_decision(inputs, expected):
    student_kw, course_kw = inputs
    student, course = make_student(**student_kw), make_course(**course_kw)
    if isinstance(expected, tuple) and expected[0] == RAISES:
        with pytest.raises(ValueError, match=f"^{expected[1]}$"):
            registration_decision(student, course)
    else:
        assert registration_decision(student, course) == expected


@pytest.mark.parametrize(
    "student_kw,course_kw",
    [
        ({"outstanding_dues": 500}, {}),
        (ALREADY, {}),
        ({}, PREQ),
        (OVER, {}),
        ({}, FULL),
        ({}, {}),
    ],
    ids=["DUES_BLOCK", "ALREADY_REGISTERED", "PREREQUISITES_MISSING",
         "CREDIT_LIMIT", "WAITLISTED", "REGISTERED"],
)
def test_ST10_decision_does_not_mutate(student_kw, course_kw):  # FR-10
    student, course = make_student(**student_kw), make_course(**course_kw)
    s0, c0 = copy.deepcopy(student), copy.deepcopy(course)
    registration_decision(student, course)
    assert student == s0
    assert course == c0


# --------------------------------------------------------------------------
# register_course / withdraw_course state changes  (FR-11 .. FR-14)
# --------------------------------------------------------------------------
def test_ST01_register_success_updates_state():
    student, course = make_student(), make_course()
    assert register_course(student, course) == "REGISTERED"
    assert "CS201" in student.registered_courses
    assert student.current_credits == 3
    assert course.enrolled == 1
    assert course.waitlist == []


def test_ST02_register_success_from_nonzero_state():
    student = make_student(current_credits=10, registered_courses={"MATH101"})
    course = make_course(credit_hours=4, enrolled=5)
    assert register_course(student, course) == "REGISTERED"
    assert student.registered_courses == {"MATH101", "CS201"}
    assert student.current_credits == 14
    assert course.enrolled == 6


def test_ST03_waitlist_appends_student_only():  # FR-12
    student, course = make_student(), make_course(enrolled=30)
    assert register_course(student, course) == "WAITLISTED"
    assert course.waitlist == ["S001"]
    assert student.registered_courses == set()
    assert student.current_credits == 0
    assert course.enrolled == 30


def test_ST04_waitlist_has_no_duplicate_entries():  # FR-12 "only if absent"
    student, course = make_student(), make_course(enrolled=30)
    register_course(student, course)
    assert register_course(student, course) == "WAITLISTED"
    assert course.waitlist == ["S001"]


@pytest.mark.parametrize(
    "student_kw,course_kw,status",
    [
        ({"outstanding_dues": 1}, {}, "DUES_BLOCK"),
        ({"outstanding_dues": 1}, {"enrolled": 30}, "DUES_BLOCK"),
        (ALREADY, {}, "ALREADY_REGISTERED"),
        ({}, PREQ, "PREREQUISITES_MISSING"),
        (OVER, {}, "CREDIT_LIMIT"),
        (OVER, FULL, "CREDIT_LIMIT"),  # credit limit outranks waitlist: no waitlist entry
    ],
    ids=["ST05-dues", "ST05-dues-full", "ST06-already", "ST07-prereq", "ST08-credit", "ST08-credit-full"],
)
def test_unsuccessful_registration_changes_nothing(student_kw, course_kw, status):  # FR-12
    student, course = make_student(**student_kw), make_course(**course_kw)
    s0, c0 = copy.deepcopy(student), copy.deepcopy(course)
    assert register_course(student, course) == status
    assert student == s0
    assert course == c0


def test_ST09_invalid_input_raises_and_changes_nothing():  # FR-15
    student, course = make_student(outstanding_dues=-5), make_course()
    s0, c0 = copy.deepcopy(student), copy.deepcopy(course)
    with pytest.raises(ValueError, match="^Invalid dues$"):
        register_course(student, course)
    assert student == s0
    assert course == c0


def test_ST11_withdraw_success_updates_state():  # FR-13, SRS scenario 6
    student = make_student(current_credits=6, registered_courses={"CS201", "MATH101"})
    course = make_course(enrolled=10)
    assert withdraw_course(student, course) is True
    assert student.registered_courses == {"MATH101"}
    assert student.current_credits == 3
    assert course.enrolled == 9


def test_ST12_withdraw_not_registered_changes_nothing():  # FR-14
    student = make_student(current_credits=3, registered_courses={"MATH101"})
    course = make_course(enrolled=10)
    s0, c0 = copy.deepcopy(student), copy.deepcopy(course)
    assert withdraw_course(student, course) is False
    assert student == s0
    assert course == c0


def test_ST13_register_then_withdraw_restores_state():
    student, course = make_student(current_credits=5), make_course(enrolled=7)
    s0, c0 = copy.deepcopy(student), copy.deepcopy(course)
    assert register_course(student, course) == "REGISTERED"
    assert withdraw_course(student, course) is True
    assert student == s0
    assert course == c0


def test_ST14_withdraw_twice_second_call_is_false():
    student, course = make_student(), make_course()
    register_course(student, course)
    assert withdraw_course(student, course) is True
    assert withdraw_course(student, course) is False
    assert student.current_credits == 0
    assert course.enrolled == 0
