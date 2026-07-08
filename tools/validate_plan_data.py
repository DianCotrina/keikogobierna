#!/usr/bin/env python3
"""Validate the src/data/plan/ tree + tracking.json."""
import json
import re
import sys
from pathlib import Path

VALID_STATUSES = {"fulfilled", "in_progress", "no_progress", "unfulfilled"}

ROOT = Path(__file__).resolve().parent.parent
PLAN_DIR = ROOT / "src" / "data" / "plan"
INDEX_PATH = PLAN_DIR / "index.json"
TOPICS_DIR = PLAN_DIR / "topics"
GOALS_PATH = PLAN_DIR / "goals" / "goals-2031.json"
TRACKING_PATH = ROOT / "src" / "data" / "tracking.json"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TOPIC_ID_RE = re.compile(r"^t\d+-\d+$")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        fail(f"cannot read/parse {path}: {e}")


def validate_index() -> dict:
    data = load_json(INDEX_PATH)

    for key in ("plan", "pillars", "topics"):
        if key not in data:
            fail(f"index.json: missing top-level key: {key}")
    if not isinstance(data["pillars"], list) or len(data["pillars"]) != 3:
        fail(f"index.json: expected 3 pillars, found {len(data.get('pillars', []))}")

    pillar_ids = set()
    for i, pillar in enumerate(data["pillars"]):
        if not isinstance(pillar, dict):
            fail(f"index.json: pillars[{i}] entry must be an object")
        for key in ("id", "name"):
            if key not in pillar:
                fail(f"index.json: pillars[{i}] missing {key}")
        if pillar["id"] in pillar_ids:
            fail(f"index.json: duplicate pillar id {pillar['id']}")
        pillar_ids.add(pillar["id"])

    topics = data["topics"]
    if not isinstance(topics, list) or len(topics) != 23:
        fail(f"index.json: expected 23 topics, found {len(topics) if isinstance(topics, list) else 'n/a'}")

    seen_topic_ids = set()
    seen_slugs = set()
    index_by_id = {}
    for i, topic in enumerate(topics):
        if not isinstance(topic, dict):
            fail(f"index.json: topics[{i}] entry must be an object")
        for key in ("id", "slug", "name", "pillar", "doc_section", "proposals", "first_100_days", "goals"):
            if key not in topic:
                fail(f"index.json: topics[{i}] missing {key}")
        tid = topic["id"]
        if not isinstance(tid, str) or not TOPIC_ID_RE.match(tid):
            fail(f"index.json: malformed topic id '{tid}' at topics[{i}]")
        if tid in seen_topic_ids:
            fail(f"index.json: duplicate topic id {tid}")
        seen_topic_ids.add(tid)
        if topic["slug"] in seen_slugs:
            fail(f"index.json: duplicate topic slug '{topic['slug']}'")
        seen_slugs.add(topic["slug"])
        if topic["pillar"] not in pillar_ids:
            fail(f"index.json: topic '{tid}' references unknown pillar '{topic['pillar']}'")
        for count_key in ("proposals", "first_100_days", "goals"):
            if not isinstance(topic[count_key], int) or isinstance(topic[count_key], bool) or topic[count_key] < 0:
                fail(f"index.json: topic '{tid}' {count_key} must be a non-negative int")
        index_by_id[tid] = topic

    return index_by_id


def validate_topics(index_by_id: dict) -> tuple[int, int, set]:
    all_proposal_ids = set()
    all_c_ids = set()
    total_proposals = 0
    total_c = 0

    for tid, topic in index_by_id.items():
        expected_files = list(TOPICS_DIR.glob(f"{tid}-*.json"))
        if len(expected_files) != 1:
            fail(f"topics/: expected exactly 1 file for topic '{tid}', found {len(expected_files)}")
        path = expected_files[0]
        data = load_json(path)

        for key in ("id", "slug", "name", "pillar", "doc_section", "groups", "first_100_days"):
            if key not in data:
                fail(f"{path.name}: missing top-level key: {key}")
        if data["id"] != tid:
            fail(f"{path.name}: id '{data['id']}' does not match index topic id '{tid}'")
        if data["slug"] != topic["slug"]:
            fail(f"{path.name}: slug '{data['slug']}' does not match index slug '{topic['slug']}'")

        groups = data["groups"]
        if not isinstance(groups, list) or not groups:
            fail(f"{path.name}: groups must be a non-empty list")

        ordinal = 0
        for gi, group in enumerate(groups):
            if not isinstance(group, dict):
                fail(f"{path.name}: groups[{gi}] entry must be an object")
            if "title" not in group:
                fail(f"{path.name}: groups[{gi}] missing 'title'")
            if group["title"] is not None and not isinstance(group["title"], str):
                fail(f"{path.name}: groups[{gi}].title must be a string or null")
            if "proposals" not in group or not isinstance(group["proposals"], list):
                fail(f"{path.name}: groups[{gi}].proposals must be a list")
            for pi, prop in enumerate(group["proposals"]):
                if not isinstance(prop, dict):
                    fail(f"{path.name}: groups[{gi}].proposals[{pi}] entry must be an object")
                if "id" not in prop or "text" not in prop:
                    fail(f"{path.name}: groups[{gi}].proposals[{pi}] missing id/text")
                ordinal += 1
                expected_id = f"{tid}.P{ordinal:02d}"
                if prop["id"] != expected_id:
                    fail(f"{path.name}: proposal ordinal mismatch — expected '{expected_id}', got '{prop['id']}'")
                if prop["id"] in all_proposal_ids:
                    fail(f"{path.name}: duplicate proposal id '{prop['id']}'")
                all_proposal_ids.add(prop["id"])
                if not isinstance(prop["text"], str) or not prop["text"].strip():
                    fail(f"{path.name}: proposal '{prop['id']}' has empty text")

        if ordinal != topic["proposals"]:
            fail(f"{path.name}: found {ordinal} proposals, index.json declares {topic['proposals']}")
        total_proposals += ordinal

        first_100_days = data["first_100_days"]
        if not isinstance(first_100_days, list):
            fail(f"{path.name}: first_100_days must be a list")
        for ci, action in enumerate(first_100_days):
            if not isinstance(action, dict):
                fail(f"{path.name}: first_100_days[{ci}] entry must be an object")
            if "id" not in action or "text" not in action:
                fail(f"{path.name}: first_100_days[{ci}] missing id/text")
            expected_id = f"{tid}.C{ci + 1:02d}"
            if action["id"] != expected_id:
                fail(f"{path.name}: first_100_days ordinal mismatch — expected '{expected_id}', got '{action['id']}'")
            if action["id"] in all_c_ids:
                fail(f"{path.name}: duplicate first_100_days id '{action['id']}'")
            all_c_ids.add(action["id"])
            if not isinstance(action["text"], str) or not action["text"].strip():
                fail(f"{path.name}: first_100_days '{action['id']}' has empty text")

        if len(first_100_days) != topic["first_100_days"]:
            fail(f"{path.name}: found {len(first_100_days)} first_100_days, index.json declares {topic['first_100_days']}")
        total_c += len(first_100_days)

    return total_proposals, total_c, all_proposal_ids | all_c_ids


def validate_goals(index_by_id: dict) -> tuple[int, set]:
    data = load_json(GOALS_PATH)
    if "goals" not in data or not isinstance(data["goals"], list):
        fail("goals-2031.json: missing/invalid top-level 'goals' list")

    goals = data["goals"]
    goal_id_re = re.compile(r"^(t\d+-\d+)\.M\d{2}$")
    all_goal_ids = set()
    per_topic_count: dict = {}

    for i, goal in enumerate(goals):
        if not isinstance(goal, dict):
            fail(f"goals-2031.json: goals[{i}] entry must be an object")
        for key in ("id", "topic", "text", "indicator", "table_topic"):
            if key not in goal:
                fail(f"goals-2031.json: goals[{i}] missing {key}")
        gid = goal["id"]
        m = goal_id_re.match(gid)
        if not m:
            fail(f"goals-2031.json: malformed goal id '{gid}' at goals[{i}]")
        if m.group(1) != goal["topic"]:
            fail(f"goals-2031.json: goal '{gid}' id/topic prefix mismatch (topic='{goal['topic']}')")
        if goal["topic"] not in index_by_id:
            fail(f"goals-2031.json: goal '{gid}' references unknown topic '{goal['topic']}'")
        if gid in all_goal_ids:
            fail(f"goals-2031.json: duplicate goal id '{gid}'")
        all_goal_ids.add(gid)
        if not isinstance(goal["text"], str) or not goal["text"].strip():
            fail(f"goals-2031.json: goal '{gid}' has empty text")
        if not isinstance(goal["indicator"], str) or not goal["indicator"].strip():
            fail(f"goals-2031.json: goal '{gid}' has empty indicator")
        if not isinstance(goal["table_topic"], str) or not goal["table_topic"].strip():
            fail(f"goals-2031.json: goal '{gid}' has empty table_topic")
        per_topic_count[goal["topic"]] = per_topic_count.get(goal["topic"], 0) + 1

    for tid in index_by_id:
        if per_topic_count.get(tid, 0) < 1:
            fail(f"goals-2031.json: topic '{tid}' has no goals (expected >=1)")
        if per_topic_count[tid] != index_by_id[tid]["goals"]:
            fail(
                f"goals-2031.json: topic '{tid}' has {per_topic_count[tid]} goals, "
                f"index.json declares {index_by_id[tid]['goals']}"
            )

    return len(goals), all_goal_ids


def validate_tracking(known_ids: set) -> None:
    data = load_json(TRACKING_PATH)

    for key in ("updated", "items", "log"):
        if key not in data:
            fail(f"tracking.json: missing top-level key: {key}")
    if not isinstance(data["updated"], str) or not DATE_RE.match(data["updated"]):
        fail(f"tracking.json: 'updated' must be YYYY-MM-DD, got '{data['updated']}'")
    if not isinstance(data["items"], dict):
        fail("tracking.json: 'items' must be a dict")
    if not isinstance(data["log"], list):
        fail("tracking.json: 'log' must be a list")

    for item_id, item in data["items"].items():
        if item_id not in known_ids:
            fail(f"tracking.json: items key '{item_id}' does not reference a known proposal/goal/100-days id")
        if not isinstance(item, dict) or "status" not in item:
            fail(f"tracking.json: items['{item_id}'] missing status")
        if item["status"] not in VALID_STATUSES:
            fail(f"tracking.json: items['{item_id}'] has invalid status '{item['status']}'")
        if "evidence" not in item or not isinstance(item["evidence"], list):
            fail(f"tracking.json: items['{item_id}'].evidence must be a list")

    for i, entry in enumerate(data["log"]):
        if not isinstance(entry, dict):
            fail(f"tracking.json: log[{i}] entry must be an object")
        for key in ("date", "item", "status", "text"):
            if key not in entry:
                fail(f"tracking.json: log[{i}] missing {key}")
        if not isinstance(entry["date"], str) or not DATE_RE.match(entry["date"]):
            fail(f"tracking.json: log[{i}].date must be YYYY-MM-DD, got '{entry['date']}'")
        if entry["item"] not in known_ids:
            fail(f"tracking.json: log[{i}].item '{entry['item']}' does not reference a known proposal/goal/100-days id")
        if entry["status"] not in VALID_STATUSES:
            fail(f"tracking.json: log[{i}].status invalid '{entry['status']}'")
        if not isinstance(entry["text"], str) or not entry["text"].strip():
            fail(f"tracking.json: log[{i}].text must be a non-empty string")


def main() -> None:
    index_by_id = validate_index()
    total_proposals, total_c, proposal_and_c_ids = validate_topics(index_by_id)
    total_goals, goal_ids = validate_goals(index_by_id)
    known_ids = proposal_and_c_ids | goal_ids
    validate_tracking(known_ids)

    print(
        f"OK: plan/ tree valid — {len(index_by_id)} topics, {total_proposals} proposals, "
        f"{total_c} first-100-days actions, {total_goals} goals; tracking.json valid"
    )


if __name__ == "__main__":
    main()
