"""Explainability and the intervention engine (Layer 4).

SHAP explains the deployed binary High-Risk classifier. An earlier version
assumed a tree model and TreeExplainer, but logistic regression is what won, so
RiskExplainer uses shap.LinearExplainer, which is exact for a linear model. LIME
is run on the same model in the notebook as a second opinion. get_interventions
turns one student's SHAP values into a ranked, actionable set of steps via
INTERVENTION_MAP.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import shap

from ml import config

logger = logging.getLogger(__name__)


# Keyed by the real DS1 feature names and the actual "bad" states a student can
# be in. A feature only produces an intervention when the student is currently
# in one of these states, so there is nothing to suggest for a good habit.
INTERVENTION_MAP: dict[str, dict] = {
    "procrastination_level": {
        "High": {
            "title": "Make starting your first task effortless",
            "why": "You told us you rarely start tasks on time and find it hard to stick "
                   "to a plan. Of everything you shared, this pattern is doing the most "
                   "to push your risk up.",
            "first_step": "Tonight, pick tomorrow's single most important task and decide "
                          "the exact time and place you will start it. When you sit down "
                          "to study, do that task first, before anything else.",
            "reframe": "Procrastination is usually about avoiding an uncomfortable "
                       "feeling, not laziness. Deciding the when and where in advance "
                       "removes the moment where you would normally slip.",
            "evidence": "implementation intentions",
            "expected_impact": "high",
        },
        "Medium": {
            "title": "Close the gap between planning and doing",
            "why": "You get to your tasks sometimes, but not consistently, and that "
                   "inconsistency is quietly adding to your risk.",
            "first_step": "Each morning, write your one must-do task on a note and set a "
                          "specific start time for it. Treat that time like a fixed "
                          "appointment you would not miss.",
            "reframe": "A task feels bigger the longer it sits undecided. Naming one "
                       "concrete next action shrinks it back to something you can start.",
            "evidence": "next-action planning",
            "expected_impact": "medium",
        },
    },
    "stress_level": {
        "High": {
            "title": "Bring your stress down before it drains your focus",
            "why": "Your self-reported stress is high, and sustained stress is one of the "
                   "strongest patterns working against your results right now.",
            "first_step": "Pick one daily anchor, like right after lunch, and take a "
                          "ten-minute walk away from screens. When it ends, note one "
                          "thing that felt a little lighter.",
            "reframe": "Stress narrows attention and makes everything feel urgent. A "
                       "short daily reset widens it again, so studying takes less effort.",
            "evidence": "arousal regulation",
            "expected_impact": "high",
            "safety": "If stress feels constant or overwhelming, talking to your "
                      "institution's counselling service is a strong and normal step.",
        },
        "Medium": {
            "title": "Keep everyday stress from building up",
            "why": "Your stress sits in the middle band. It is manageable now, but left "
                   "unchecked it tends to creep into your focus and your sleep.",
            "first_step": "Before your first study block, take five slow breaths, four "
                          "seconds in and six seconds out. Let that be the signal that "
                          "study time has started.",
            "reframe": "A slow exhale tells your body it is safe to concentrate. Pairing "
                       "it with study turns it into a cue rather than a chore.",
            "evidence": "paced breathing",
            "expected_impact": "medium",
        },
    },
    "sleep_hours": {
        "4–5 hours": {
            "title": "Protect the sleep your focus depends on",
            "why": "You are running on four to five hours. At that level, attention, "
                   "memory, and mood all take a measurable hit, and it shows in your risk.",
            "first_step": "Set a fixed wake time for the next three days and count back "
                          "eight hours for a target lights-out. Thirty minutes before "
                          "that, put your phone to charge in another room.",
            "reframe": "You cannot force sleep, but you can protect the runway to it. A "
                       "steady wake time and a screen-free wind-down do most of the work.",
            "evidence": "sleep hygiene",
            "expected_impact": "high",
        },
        "6–7 hours": {
            "title": "Turn decent sleep into reliable sleep",
            "why": "Six to seven hours is close, but the night-to-night swings are likely "
                   "costing you some of the focus you are studying for.",
            "first_step": "Keep your wake time the same on weekends, within an hour, and "
                          "anchor it to something you already do, like your morning drink.",
            "reframe": "Consistency matters as much as total hours. A steady rhythm lets "
                       "your body prepare for sleep before you even lie down.",
            "evidence": "circadian consistency",
            "expected_impact": "medium",
        },
    },
    "study_hours_daily": {
        "Less than 1 hour": {
            "title": "Add one protected hour of real study",
            "why": "You are studying under an hour on a typical day. For a technical "
                   "course that is below what the material needs, and it is a large part "
                   "of your risk.",
            "first_step": "Block one hour tomorrow at a set time, in a place with no "
                          "phone. Spend it on the subject you are most behind on, for "
                          "that hour only.",
            "reframe": "You do not need a perfect study system, just one hour that "
                       "reliably happens. Consistency beats intensity you cannot sustain.",
            "evidence": "time-boxing",
            "expected_impact": "high",
        },
    },
    "focus_duration": {
        "30–60 minutes": {
            "title": "Stretch your focus with a gentle interval",
            "why": "Your longest focused stretch is under an hour. That is workable, but "
                   "it means deeper topics get interrupted before they click.",
            "first_step": "Next session, set a timer for forty minutes of single-task "
                          "work, then take a real ten-minute break. Do just two rounds.",
            "reframe": "Focus is trainable like a muscle. Short, protected intervals "
                       "build it faster than long sessions you cannot hold.",
            "evidence": "attention interval training",
            "expected_impact": "medium",
        },
    },
    "screen_time_non_study": {
        "More than 6 hours": {
            "title": "Put friction between you and the endless scroll",
            "why": "More than six hours of non-study screen time is competing directly "
                   "with the focus your course needs, and it shows in your risk.",
            "first_step": "During your next study block, leave your phone in another room, "
                          "not face-down on the desk. Distance, not willpower, is what "
                          "works.",
            "reframe": "Attention follows the path of least resistance. Making the "
                       "distraction harder to reach beats trying to resist it.",
            "evidence": "stimulus control",
            "expected_impact": "high",
        },
    },
    "attendance_percentage": {
        "Less than 50%": {
            "title": "Get back into the room, one class at a time",
            "why": "Your attendance is under half. Missing that much class is one of the "
                   "clearest signals in your profile, because it compounds across every "
                   "topic.",
            "first_step": "Pick the one subject you are most behind in and commit to its "
                          "next three classes. Sit near the front.",
            "reframe": "You do not have to fix all of it at once. Rebuilding attendance "
                       "in one subject creates momentum that carries to the rest.",
            "evidence": "graded re-entry",
            "expected_impact": "high",
        },
        "50% – 65%": {
            "title": "Close the attendance gap before it widens",
            "why": "You are missing a meaningful share of classes. Each miss is a topic "
                   "you later have to learn alone, which quietly raises your risk.",
            "first_step": "For the next two weeks, treat one specific class as "
                          "non-negotiable and build the rest of your day around it.",
            "reframe": "Attendance is less about rules and more about not creating future "
                       "debt for yourself. Present-you saves future-you the catch-up.",
            "evidence": "commitment device",
            "expected_impact": "medium",
        },
        "66% – 75%": {
            "title": "Nudge attendance into the safe zone",
            "why": "Your attendance is on the low side, close enough to a threshold that "
                   "a couple of bad weeks could tip it.",
            "first_step": "Name the one class you skip most often and decide, now, the "
                          "reason you will attend it this week.",
            "reframe": "A small, steady presence is easier to keep than a dramatic "
                       "catch-up later. Protect the habit while the fix is still small.",
            "evidence": "if-then planning",
            "expected_impact": "medium",
        },
    },
    "career_goal_clarity": {
        "Not clear": {
            "title": "Give your effort a direction to aim at",
            "why": "You said your career direction is not clear yet. Without a target, "
                   "motivation is harder to sustain, and that uncertainty is part of "
                   "your risk.",
            "first_step": "This week, message two seniors or alumni working in areas you "
                          "find interesting and ask each of them one question about how "
                          "they started.",
            "reframe": "Clarity comes from small exposures, not from waiting to feel "
                       "certain. One honest conversation usually beats a week of "
                       "overthinking.",
            "evidence": "exploration over rumination",
            "expected_impact": "medium",
        },
        "Somewhat clear": {
            "title": "Sharpen a rough direction into a real plan",
            "why": "You have a rough sense of direction but it is not concrete yet, and "
                   "that fuzziness makes it easy to drift.",
            "first_step": "Write down two or three target roles, then pick one skill each "
                          "needs and one small step toward it this month.",
            "reframe": "A vague goal cannot pull you forward. Naming specific roles turns "
                       "motivation into something you can act on.",
            "evidence": "goal specificity",
            "expected_impact": "medium",
        },
    },
    "events_participation": {
        "Never participate in such events": {
            "title": "Use one event to build momentum and contacts",
            "why": "You have not been taking part in events or hackathons. For a "
                   "technical student that is a missed source of motivation, peers, and "
                   "proof of skill.",
            "first_step": "Find one hackathon or department event this term and register "
                          "for it, aiming to learn rather than to win.",
            "reframe": "You do not join events because you are ready; you get ready by "
                       "joining. The first one is the hardest and the most useful.",
            "evidence": "action precedes confidence",
            "expected_impact": "medium",
        },
    },
    "projects_internships": {
        "Not currently, but intend to in the future": {
            "title": "Turn someday into one project you start now",
            "why": "You intend to work on projects or internships but have not started. "
                   "Intent without a first move tends to stay intent.",
            "first_step": "This week, start one small portfolio project or send three "
                          "internship applications, including to startups and labs, not "
                          "only large firms.",
            "reframe": "A small finished project beats a big imagined one. Starting tiny "
                       "is what makes the next step obvious.",
            "evidence": "bias to action",
            "expected_impact": "medium",
        },
    },
}

# The healthy value each driver is nudged toward when the prediction pipeline
# estimates how far a recommendation could move the risk signal. Ordinal targets
# use the exact band strings the model was trained on; procrastination is
# translated to its source behaviours by the inference layer.
INTERVENTION_HEALTHY_TARGET: dict[str, object] = {
    "procrastination_level": "Low",
    "stress_level": 2,
    "sleep_hours": "6–7 hours",
    "study_hours_daily": "More than 2 hours",
    "focus_duration": "More than 2 hours",
    "screen_time_non_study": "2–4 hours",
    "attendance_percentage": "Above 85%",
    "career_goal_clarity": "Very clear",
    "events_participation": "Occasionally participate in events",
    "projects_internships": "Yes, actively working on projects/internship",
}

# ---------------------------------------------------------------------------
# Phase 2: personalisation tables
# ---------------------------------------------------------------------------
# The barrier a student names for themselves is a readiness signal, so a matching
# driver is boosted and acknowledged. Maps the four internal_barrier options to
# the drivers they most relate to.
BARRIER_RELATED_DRIVERS: dict[str, set] = {
    "Procrastination / Low Motivation": {"procrastination_level"},
    "Lack of Consistency or Determination (Difficulty sticking to a plan)": {
        "procrastination_level",
        "study_hours_daily",
    },
    "Poor Time Management / Over-scheduling": {"procrastination_level", "study_hours_daily"},
    "Difficulty with Focus / Concentration": {"focus_duration", "screen_time_non_study"},
}

# Per-persona lead drivers and an opening line, keyed to the deterministic KMeans
# cluster ids. A driver in a persona's lead set gets a smaller boost, so the plan
# leads with what that group usually needs first.
PERSONA_GUIDANCE: dict[int, dict] = {
    0: {  # Distracted Coasters / "Capable but Coasting"
        "lead": [
            "procrastination_level",
            "screen_time_non_study",
            "study_hours_daily",
            "events_participation",
            "projects_internships",
        ],
        "intro": "You clearly have the ability. The gap is turning it into steady action, "
                 "and these are aimed right at that.",
    },
    1: {  # Driven Achievers
        "lead": [],
        "intro": "You are on a strong, steady track. Treat these as small tune-ups, not fixes.",
    },
    2: {  # Focused High-Performers
        "lead": ["stress_level", "sleep_hours"],
        "intro": "You put in the work. These are about protecting the energy and wellbeing "
                 "that keep it sustainable.",
    },
    3: {  # Burnt-out Strugglers / "Under Pressure"
        "lead": ["stress_level", "sleep_hours"],
        "intro": "You are carrying a lot right now, so let's keep this to one thing at a time "
                 "and build from there.",
    },
}

# When two chosen drivers reinforce each other, add a short connecting note to the
# carrier card so the plan reads as a sequence rather than a list. Each rule is
# (the pair of drivers, the card that carries the note, the note).
CO_OCCURRENCE: list[tuple] = [
    (
        {"stress_level", "procrastination_level"},
        "procrastination_level",
        "High stress often feeds procrastination, so easing the stress first can make "
        "starting tasks easier.",
    ),
    (
        {"sleep_hours", "focus_duration"},
        "focus_duration",
        "Short sleep pulls focus down, so the sleep change tends to make focusing easier too.",
    ),
    (
        {"screen_time_non_study", "study_hours_daily"},
        "study_hours_daily",
        "Your screen time and study time compete for the same hours, so winning one usually "
        "helps the other.",
    ),
    (
        {"stress_level", "sleep_hours"},
        "sleep_hours",
        "Stress and short sleep feed each other, so improving one often eases the other.",
    ),
]

# Phase 3 (storage-free part): alternate phrasings for the highest-traffic cards.
# One of the two wordings is chosen deterministically per student, so different
# students in the same state do not all read the identical paragraph, while the
# same student always sees the same wording. When a feedback store exists later,
# these become the arms of an A/B test; for now they only add variety.
INTERVENTION_VARIANTS: dict[tuple, dict] = {
    ("procrastination_level", "High"): {
        "first_step": "Right now, shrink tomorrow's biggest task to a five-minute version you "
                      "cannot say no to, and decide when you will do it. Starting is the whole "
                      "battle; momentum handles the rest.",
        "reframe": "The hardest part is almost never the work, it is the starting. Make the "
                   "first move small enough that starting feels easy, and the task tends to "
                   "pull you along.",
    },
    ("stress_level", "High"): {
        "first_step": "Choose one thing to take off your plate this week, even a small one, and "
                      "protect a single screen-free half hour a day to reset.",
        "reframe": "You cannot pour from an empty cup. Easing the load a little is not falling "
                   "behind, it is what makes the rest of the work possible.",
    },
    ("sleep_hours", "4–5 hours"): {
        "first_step": "For the next three nights, pick a fixed lights-out time and set an alarm "
                      "to start winding down thirty minutes before it, with your phone charging "
                      "outside the room.",
        "reframe": "Sleep is not time taken from study, it is what makes study stick. A rested "
                   "hour is worth two tired ones.",
    },
    ("study_hours_daily", "Less than 1 hour"): {
        "first_step": "Pick one subject and one fixed hour tomorrow, and treat it like a class "
                      "you cannot skip. One reliable hour beats three you keep planning.",
        "reframe": "Motivation follows action, not the other way round. A short scheduled block "
                   "that actually happens builds the habit that longer sessions never will.",
    },
}

# When a student has no risk-increasing habit to fix, the plan should not be a
# dead end. These are per-persona maintenance habits: how to stay consistent and
# protect what is already working, tailored to what that group tends to need.
PERSONA_MAINTENANCE: dict[int, list] = {
    0: [  # Distracted Coasters / "Capable but Coasting"
        {
            "title": "Anchor your day with one fixed block",
            "detail": "Put a single, same-time study block on the calendar each day. A steady "
                      "anchor is what turns capability into consistent output.",
        },
        {
            "title": "Keep one point of accountability",
            "detail": "Tell a friend or a group your one goal for the week. A little outside "
                      "accountability keeps momentum when motivation dips.",
        },
    ],
    1: [  # Driven Achievers
        {
            "title": "Protect the routine that got you here",
            "detail": "Your consistency is your edge. Guard the daily rhythm, and treat a missed "
                      "day as a blip to reset from, not a reason to drift.",
        },
        {
            "title": "Guard your sleep and downtime",
            "detail": "Consistency tips into burnout without recovery. Keep a firm wind-down and "
                      "one genuine rest block each week.",
        },
        {
            "title": "Set one small stretch goal",
            "detail": "To stay engaged, pick one thing slightly beyond your current level each "
                      "month: a harder problem set, a new tool, or a project.",
        },
    ],
    2: [  # Focused High-Performers
        {
            "title": "Build in real recovery",
            "detail": "Intensity is only sustainable with rest. Schedule breaks the way you "
                      "schedule study, and protect at least one lighter day.",
        },
        {
            "title": "Treat sleep as performance, not a luxury",
            "detail": "Your output depends on it. Keep a consistent sleep window even in the "
                      "crunch weeks.",
        },
        {
            "title": "Vary the work to avoid tunnel vision",
            "detail": "Rotate subjects or methods so deep focus does not narrow into fatigue.",
        },
    ],
    3: [  # Burnt-out Strugglers / "Under Pressure"
        {
            "title": "Keep the small wellbeing routines",
            "detail": "Whatever reset is working, a walk, breathing, a screen-free hour, keep it "
                      "daily. It is doing more than it feels like.",
        },
        {
            "title": "Hold one steady habit before adding another",
            "detail": "You do not have to fix everything at once. Protect one routine this week, "
                      "then build from there.",
        },
    ],
}
PERSONA_MAINTENANCE_DEFAULT = [
    {
        "title": "Keep a steady daily rhythm",
        "detail": "A consistent study block, decent sleep, and a short daily review protect the "
                  "habits that are already working.",
    },
    {
        "title": "Check in with yourself weekly",
        "detail": "A five-minute weekly look at what went well and what slipped keeps small "
                  "drifts from becoming big ones.",
    },
]


def _pick_variant(student_features: dict, feature: str, n: int = 2) -> int:
    """Choose a copy variant deterministically for this student and driver.

    Seeded from a few stable answers plus the driver name, so the same student
    sees the same wording every time while different students vary. Uses a fixed
    hash (not Python's per-process hash) so the choice is stable across restarts.
    """
    stable = "|".join(
        str(student_features.get(key, ""))
        for key in ("cgpa_category", "program_stream", "year_class", "age", "stress_level")
    )
    digest = hashlib.md5(f"{stable}|{feature}".encode()).hexdigest()
    return int(digest, 16) % n


def _bucket_value(feature: str, value) -> Optional[str]:
    """Turn a student's raw value into an intervention bucket key.

    stress_level is numeric so it gets thresholded; everything else just matches
    its value against the map keys. Returns None when there is no intervention
    for the current value.
    """
    options = INTERVENTION_MAP[feature]
    if feature == "stress_level":
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric >= 3.5:
            return "High"
        if numeric >= 2.5:
            return "Medium"
        return None
    return value if value in options else None


def get_interventions(
    student_features: dict,
    shap_values_for_student: np.ndarray,
    feature_names: list[str],
    top_n: Optional[int] = None,
) -> list[dict]:
    """Build the candidate interventions for a student.

    A driver qualifies when it is in an addressable bad state (present in
    INTERVENTION_MAP with a matching bucket). Unlike a pure SHAP filter, this does
    not drop a driver just because the model attributes its risk to correlated
    source features (procrastination is the clear case, since its signal is shared
    with study consistency and punctuality). Each candidate carries the driver, the
    current value, the SHAP impact (kept for the drivers chart and as a tiebreak),
    and the authored content with a deterministically chosen wording variant. The
    final filtering by real impact and the ordering are done by the pipeline and
    `personalize`.
    """
    shap_by_feature = dict(zip(feature_names, shap_values_for_student))

    scored = []
    for feature in INTERVENTION_MAP:
        impact = float(shap_by_feature.get(feature, 0.0))
        bucket = _bucket_value(feature, student_features.get(feature))
        entry = INTERVENTION_MAP[feature].get(bucket) if bucket else None
        if entry is None:
            continue
        scored.append((feature, bucket, student_features.get(feature), impact, entry))

    scored.sort(key=lambda item: item[3], reverse=True)

    interventions = []
    for feature, bucket, current_value, impact, entry in scored[:top_n]:
        first_step = entry["first_step"]
        reframe = entry["reframe"]
        if _pick_variant(student_features, feature):
            alt = INTERVENTION_VARIANTS.get((feature, bucket))
            if alt:
                first_step = alt.get("first_step", first_step)
                reframe = alt.get("reframe", reframe)
        intervention = {
            "feature": feature,
            "current_value": current_value,
            "shap_impact": round(impact, 4),
            "title": entry["title"],
            "why": entry["why"],
            "first_step": first_step,
            "reframe": reframe,
            "evidence": entry["evidence"],
            "expected_impact": entry["expected_impact"],
        }
        if entry.get("safety"):
            intervention["safety"] = entry["safety"]
        interventions.append(intervention)
    return interventions


def get_risk_drivers(
    shap_values_for_student: np.ndarray,
    feature_names: list[str],
    student_features: dict,
    top_n: int = 6,
) -> list[dict]:
    """Top interpretable behaviours pushing this student toward High Risk.

    For the "what is influencing your risk" chart, kept separate from the action
    cards so the two views can differ honestly (one explains, one prescribes).
    Restricted to the readable single-column features (numerics, ordinal bands,
    and procrastination), so the labels stay clean and one-hot columns never leak
    in. As an explanation it can include drivers that are not directly actionable,
    such as the CGPA band.
    """
    interpretable = (
        set(config.DS1_NUMERIC_FEATURES)
        | set(config.DS1_ORDINAL_FEATURES)
        | {config.PROCRASTINATION_FEATURE}
    )
    shap_by_feature = dict(zip(feature_names, shap_values_for_student))
    rows = []
    for feature, value in shap_by_feature.items():
        if feature not in interpretable:
            continue
        impact = float(value)
        if impact <= 0:
            continue
        rows.append(
            {
                "feature": feature,
                "current_value": student_features.get(feature),
                "shap_impact": round(impact, 4),
            }
        )
    rows.sort(key=lambda row: row["shap_impact"], reverse=True)
    return rows[:top_n]


def get_strengths(
    shap_values_for_student: np.ndarray,
    feature_names: list[str],
    student_features: dict,
    top_n: int = 3,
) -> list[dict]:
    """The behaviours most protecting this student, their strongest habits.

    The mirror of `get_risk_drivers`: the interpretable behavioural features with
    the most negative SHAP (the ones lowering risk). Used to name a well-doing
    student's anchors so the maintenance view feels tailored rather than generic.
    """
    behavioural = set(config.DS1_CLUSTER_FEATURES) | {"attendance_percentage"}
    shap_by_feature = dict(zip(feature_names, shap_values_for_student))
    rows = []
    for feature, value in shap_by_feature.items():
        if feature not in behavioural:
            continue
        impact = float(value)
        if impact >= 0:
            continue
        rows.append(
            {
                "feature": feature,
                "current_value": student_features.get(feature),
                "shap_impact": round(impact, 4),
            }
        )
    rows.sort(key=lambda row: row["shap_impact"])
    return rows[:top_n]


def build_maintenance(
    shap_values_for_student: np.ndarray,
    feature_names: list[str],
    student_features: dict,
    cluster_id: int,
    top_n: int = 3,
) -> dict:
    """A protective, persona-tailored plan for a student with nothing urgent to fix.

    Names the student's strongest habits (their anchors) and pairs them with the
    maintenance habits that persona usually needs to stay consistent, so a
    well-doing student gets forward guidance instead of a dead end.
    """
    return {
        "strengths": get_strengths(
            shap_values_for_student, feature_names, student_features, top_n=top_n
        ),
        "habits": PERSONA_MAINTENANCE.get(cluster_id, PERSONA_MAINTENANCE_DEFAULT),
    }


def personalize(
    interventions: list[dict],
    student_input: dict,
    cluster_id: int,
    risk_probability: float,
    top_n: int = 3,
) -> tuple[list[dict], dict]:
    """Choose, order, and annotate the candidates for this specific student.

    A driver is eligible if the model sees it pushing risk up (positive SHAP) or
    it is the driver the student named as their barrier and is in a bad state. The
    barrier clause is what keeps a genuine but collinear driver like procrastination
    from being hidden, since its own SHAP is often near zero. If nothing is
    eligible the student gets the reassuring empty state. Ranking is SHAP magnitude
    plus two additive, SHAP-scaled boosts (a larger one for the named barrier, a
    smaller one for a persona's lead drivers), so a boost can lift a low-SHAP
    barrier into view without dethroning a genuinely dominant driver. It then adds
    a connecting note where two chosen drivers reinforce each other, and a
    "focus on one" dose signal for students already under pressure. The impact
    number on each card comes separately from the counterfactual risk-drop, shown
    only when it is meaningful. Returns the final list and a guidance block.
    """
    barrier = student_input.get("internal_barrier")
    barrier_drivers = BARRIER_RELATED_DRIVERS.get(barrier, set())
    persona = PERSONA_GUIDANCE.get(cluster_id, {})
    lead = set(persona.get("lead", []))

    eligible = [
        item
        for item in interventions
        if item["shap_impact"] > 0 or item["feature"] in barrier_drivers
    ]
    if not eligible:
        return [], {"intro": persona.get("intro", ""), "focus_one": False}

    max_shap = max((abs(item["shap_impact"]) for item in eligible), default=1.0) or 1.0
    for item in eligible:
        feature = item["feature"]
        item["acknowledged"] = feature in barrier_drivers
        boost = (0.5 * max_shap if item["acknowledged"] else 0.0) + (
            0.25 * max_shap if feature in lead else 0.0
        )
        item["_score"] = abs(item["shap_impact"]) + boost

    ordered = sorted(eligible, key=lambda item: item["_score"], reverse=True)[:top_n]
    for priority, item in enumerate(ordered, start=1):
        item["priority"] = priority
        item["is_primary"] = priority == 1
        item.pop("_score", None)

    present = {item["feature"] for item in ordered}
    by_feature = {item["feature"]: item for item in ordered}
    for pair, carrier, note in CO_OCCURRENCE:
        if pair <= present and carrier in by_feature and "bridge" not in by_feature[carrier]:
            by_feature[carrier]["bridge"] = note

    try:
        stress = float(student_input.get("stress_level"))
    except (TypeError, ValueError):
        stress = None
    focus_one = cluster_id == 3 or (stress is not None and stress >= 4) or risk_probability >= 0.9

    return ordered, {"intro": persona.get("intro", ""), "focus_one": bool(focus_one)}


class RiskExplainer:
    """SHAP over the deployed binary (High Risk) logistic pipeline."""

    def __init__(self, model_pipeline, feature_names: list[str]) -> None:
        self.pipeline = model_pipeline
        self.scaler = model_pipeline.named_steps["scaler"]
        self.model = model_pipeline.named_steps["model"]
        self.feature_names = list(feature_names)
        self.explainer_ = None
        self.expected_value_: Optional[float] = None

    def fit(self, background_features: pd.DataFrame) -> "RiskExplainer":
        """Fit the linear explainer using the scaled training data as background."""
        scaled_background = self.scaler.transform(background_features)
        self.explainer_ = shap.LinearExplainer(self.model, scaled_background)
        self.expected_value_ = self.explainer_.expected_value
        return self

    def shap_values(self, features: pd.DataFrame) -> np.ndarray:
        """SHAP values for the positive class (n_samples x n_features)."""
        return self.explainer_.shap_values(self.scaler.transform(features))

    def scaled_frame(self, features: pd.DataFrame) -> pd.DataFrame:
        """Scaled features as a named dataframe, which the SHAP plots want."""
        return pd.DataFrame(
            self.scaler.transform(features), columns=self.feature_names, index=features.index
        )

    def mean_abs_shap(self, features: pd.DataFrame) -> pd.Series:
        """Global importance: mean absolute SHAP per feature, sorted high to low."""
        values = np.abs(self.shap_values(features)).mean(axis=0)
        return pd.Series(values, index=self.feature_names).sort_values(ascending=False)

    def plot_beeswarm(self, features: pd.DataFrame, save_path: Optional[Path] = None):
        import matplotlib.pyplot as plt

        shap.summary_plot(
            self.shap_values(features), self.scaled_frame(features),
            feature_names=self.feature_names, show=False, max_display=15,
        )
        fig = plt.gcf()
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=120, bbox_inches="tight")
        return fig

    def plot_bar(self, features: pd.DataFrame, save_path: Optional[Path] = None):
        import matplotlib.pyplot as plt

        shap.summary_plot(
            self.shap_values(features), self.scaled_frame(features),
            feature_names=self.feature_names, plot_type="bar", show=False, max_display=15,
        )
        fig = plt.gcf()
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=120, bbox_inches="tight")
        return fig

    def plot_dependence(self, feature: str, features: pd.DataFrame, interaction: Optional[str] = None,
                        save_path: Optional[Path] = None):
        import matplotlib.pyplot as plt

        shap.dependence_plot(
            feature, self.shap_values(features), self.scaled_frame(features),
            interaction_index=interaction, show=False,
        )
        fig = plt.gcf()
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, dpi=120, bbox_inches="tight")
        return fig

    def force_plot_html(self, features: pd.DataFrame, row_index: int, save_path: Path) -> None:
        """Save an interactive HTML force plot for one student."""
        scaled = self.scaled_frame(features)
        values = self.shap_values(features)
        plot = shap.force_plot(
            self.expected_value_, values[row_index], scaled.iloc[row_index],
            feature_names=self.feature_names,
        )
        shap.save_html(str(save_path), plot)

