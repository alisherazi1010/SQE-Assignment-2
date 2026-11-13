"""White-box tests for registration_decision() and register_course().

Expected results still come from REQUIREMENTS.md; the code is used only to choose
inputs that reach specific paths, branches and conditions.

Condition-level CFG node labels (see docs/cfg.png):
  d1  dues < 0                       d5  not prerequisites_satisfied(...)
  d2a 0 <= enrolled                  d6  not check_credit_limit(...)
  d2b enrolled <= capacity           d7  enrolled > capacity
  d2c capacity < 1                   d3  dues > 1000   d4  code in registered
"""
import copy

import pytest

from registration import (
    Student,
    Course,
    registration_decision,
    register_course,
    withdraw_course,
)


def S(**kw):
    kw.setdefault("student_id", "S001")
    return Student(**copy.deepcopy(kw))


def C(**kw):
    kw.setdefault("code", "CS201")
    kw.setdefault("credit_hours", 3)
    kw.setdefault("capacity", 30)
    return Course(**copy.deepcopy(kw))


# ------------------------------------------------------------------ basis paths
# V(G) = 10 (condition-level CFG). One test per independent path.
def test_WB_P01_d1_true_invalid_dues():
    """Path P1: d1=T -> raise 'Invalid dues'."""
    with pytest.raises(ValueError, match="^Invalid dues$"):
        registration_decision(S(outstanding_dues=-1), C())


def test_WB_P02_d2a_false_negative_enrolled():
    """Path P2: d1=F, d2a=F (enrolled=-1) -> raise 'Invalid capacity or enrollment'."""
    with pytest.raises(ValueError, match="^Invalid capacity or enrollment$"):
        registration_decision(S(), C(enrolled=-1))


def test_WB_P03_d2b_false_enrolled_above_capacity():
    """Path P3: d2a=T, d2b=F (enrolled=31 > capacity=30) -> raise."""
    with pytest.raises(ValueError, match="^Invalid capacity or enrollment$"):
        registration_decision(S(), C(enrolled=31))


def test_WB_P04_d2c_true_capacity_zero():
    """Path P4: d2a=T, d2b=T, d2c=T (capacity=0, enrolled=0) -> raise."""
    with pytest.raises(ValueError, match="^Invalid capacity or enrollment$"):
        registration_decision(S(), C(capacity=0, enrolled=0))


def test_WB_P05_d3_true_dues_block():
    """Path P5: d3=T. dues=1001 (> any threshold) so the DUES_BLOCK return is reached."""
    assert registration_decision(S(outstanding_dues=1001), C()) == "DUES_BLOCK"


def test_WB_P06_d4_true_already_registered():
    """Path P6: d3=F, d4=T."""
    assert registration_decision(S(registered_courses={"CS201"}), C()) == "ALREADY_REGISTERED"


def test_WB_P07_d5_true_prerequisites_missing():
    """Path P7: d4=F, d5=T."""
    assert registration_decision(S(), C(prerequisites={"CS101"})) == "PREREQUISITES_MISSING"


def test_WB_P08_d6_true_credit_limit():
    """Path P8: d5=F, d6=T (16 + 3 = 19 > 18)."""
    assert registration_decision(S(current_credits=16), C()) == "CREDIT_LIMIT"


def test_WB_P09_d7_true_waitlisted():
    """Path P9: d6=F, d7=T. Course full (30/30) must give WAITLISTED (FR-08)."""
    assert registration_decision(S(), C(enrolled=30)) == "WAITLISTED"


def test_WB_P10_d7_false_registered():
    """Path P10 (baseline): every decision False -> REGISTERED."""
    assert registration_decision(S(), C()) == "REGISTERED"


# ------------------------------------------------------------------ MC/DC
# Decision: raise if  (not (A and B)) or C   A: 0<=enrolled  B: enrolled<=capacity  C: capacity<1
# Short-circuit truth table (NE = not evaluated):
#   T1: A=F B=NE C=NE -> raise      T3: A=T B=T C=T -> raise
#   T2: A=T B=F  C=NE -> raise      T4: A=T B=T C=F -> no raise
# Independence pairs: A:(T1,T4)  B:(T2,T4)  C:(T3,T4)
MSG = "^Invalid capacity or enrollment$"


def test_WB_MCDC_T1_A_false():
    """MC/DC T1: A=F (enrolled=-1). Pair with T4 shows A flips the outcome."""
    with pytest.raises(ValueError, match=MSG):
        registration_decision(S(), C(enrolled=-1))


def test_WB_MCDC_T2_B_false():
    """MC/DC T2: A=T, B=F (enrolled=31, capacity=30). Pair with T4 shows B flips the outcome."""
    with pytest.raises(ValueError, match=MSG):
        registration_decision(S(), C(enrolled=31, capacity=30))


def test_WB_MCDC_T3_C_true():
    """MC/DC T3: A=T, B=T, C=T (capacity=0, enrolled=0). Pair with T4 shows C flips the outcome."""
    with pytest.raises(ValueError, match=MSG):
        registration_decision(S(), C(enrolled=0, capacity=0))


def test_WB_MCDC_T4_all_valid():
    """MC/DC T4: A=T, B=T, C=F -> validation passes (decision False)."""
    assert registration_decision(S(), C(enrolled=0, capacity=30)) in {"REGISTERED", "WAITLISTED"}


# ------------------------------------------------------------------ structural gap tests (B2)
def test_WB_G01_register_course_waitlist_append_branch():
    """Gap: register_course 'WAITLISTED and id not in waitlist' True branch (FR-12)."""
    student, course = S(), C(enrolled=30)
    assert register_course(student, course) == "WAITLISTED"
    assert course.waitlist == ["S001"]


def test_WB_G02_register_course_waitlist_already_present_branch():
    """Gap: 'WAITLISTED' with id already in waitlist -> False side of the 'and' (FR-12)."""
    student, course = S(), C(enrolled=30, waitlist=["S001"])
    assert register_course(student, course) == "WAITLISTED"
    assert course.waitlist == ["S001"]


def test_WB_G03_register_course_other_status_no_branch():
    """Gap: register_course with a status that is neither REGISTERED nor WAITLISTED."""
    student, course = S(outstanding_dues=1001), C()
    assert register_course(student, course) == "DUES_BLOCK"
    assert student.registered_courses == set()
    assert course.enrolled == 0


def test_WB_G04_withdraw_both_branches():
    """withdraw_course: not-registered branch, then registered branch."""
    student, course = S(), C(enrolled=1)
    assert withdraw_course(student, course) is False
    student.registered_courses.add("CS201")
    student.current_credits = 3
    assert withdraw_course(student, course) is True
    assert course.enrolled == 0  # FR-13: enrolled decrements by one
