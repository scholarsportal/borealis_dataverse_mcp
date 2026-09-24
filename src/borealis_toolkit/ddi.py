from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET

from .errors import BorealisError

_STAT_KEY_MAP = {
    "min": "min",
    "max": "max",
    "mean": "mean",
    "medn": "median",
    "stdev": "stddev",
    "mode": "mode",
    "vald": "valid_cases",
    "invd": "invalid_cases",
}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(elem: ET.Element | None, name: str) -> ET.Element | None:
    if elem is None:
        return None
    for node in elem:
        if _local_name(node.tag) == name:
            return node
    return None


def _children(elem: ET.Element, name: str) -> list[ET.Element]:
    return [node for node in elem if _local_name(node.tag) == name]


def _text(elem: ET.Element | None) -> str | None:
    if elem is None:
        return None
    value = "".join(elem.itertext()).strip()
    return value or None


def _safe_fromstring(xml_text: str) -> ET.Element:
    # DDI codebooks never need a DTD, so refusing DOCTYPE/ENTITY declarations
    # outright blocks entity-expansion attacks without an extra dependency.
    if "<!DOCTYPE" in xml_text or "<!ENTITY" in xml_text:
        raise BorealisError("DDI XML contains a DOCTYPE or ENTITY declaration; refusing to parse it.")
    try:
        return ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise BorealisError(f"Malformed DDI XML: {exc}") from exc


def _number(text: str) -> Any:
    try:
        as_float = float(text)
    except ValueError:
        return text
    return int(as_float) if as_float.is_integer() else as_float


def parse_ddi_variables(
    xml_text: str,
    *,
    include_summary_stats: bool = True,
    max_variables: int | None = 50,
    offset: int = 0,
    name_filter: str | None = None,
) -> tuple[list[dict[str, Any]], int, int]:
    """Parse a DDI codebook XML document into variable dicts.

    Returns (variables, matched_count, total_variable_count). name_filter is a
    case-insensitive substring matched against each variable's name or label;
    offset and max_variables (None = no limit) page through the matches.
    Namespaces are stripped before matching tag names so this works across the
    DDI codebook namespace URIs different Dataverse installs declare (e.g.
    'ddi:codebook:2_5' vs. 'http://www.icpsr.umich.edu/DDI'), without
    hard-coding one of them.
    """
    root = _safe_fromstring(xml_text)
    data_dscr = next((elem for elem in root.iter() if _local_name(elem.tag) == "dataDscr"), None)
    if data_dscr is None:
        return [], 0, 0

    var_elements = _children(data_dscr, "var")
    total = len(var_elements)
    if name_filter:
        needle = name_filter.lower()
        var_elements = [
            var for var in var_elements
            if needle in (var.get("name") or "").lower() or needle in (_text(_child(var, "labl")) or "").lower()
        ]
    matched = len(var_elements)
    end = None if max_variables is None else offset + max_variables
    groups = _variable_groups(data_dscr)
    variables = [
        _parse_variable(var, include_summary_stats=include_summary_stats, groups=groups)
        for var in var_elements[offset:end]
    ]
    return variables, matched, total


def _variable_groups(data_dscr: ET.Element) -> dict[str, list[str]]:
    """Map variable ID -> names of the varGrp elements that list it."""
    groups: dict[str, list[str]] = {}
    for grp in _children(data_dscr, "varGrp"):
        name = _text(_child(grp, "labl")) or grp.get("name") or grp.get("ID")
        if not name:
            continue
        for var_id in (grp.get("var") or "").split():
            groups.setdefault(var_id, []).append(name)
    return groups


def documentation_coverage(variables: list[dict[str, Any]]) -> dict[str, int]:
    """Count how many variables carry each kind of reuse documentation.

    Value labels are only expected of categorical variables (those with
    category entries), so they get their own denominator.
    """
    return {
        "variables": len(variables),
        "labelled": sum(1 for v in variables if v.get("label")),
        "categorical": sum(1 for v in variables if v.get("categorical")),
        "value_labelled": sum(1 for v in variables if v.get("categorical") and v.get("value_labels")),
        "with_question_text": sum(1 for v in variables if v.get("question_text")),
    }


def _parse_variable(var: ET.Element, *, include_summary_stats: bool, groups: dict[str, list[str]]) -> dict[str, Any]:
    var_format = _child(var, "varFormat")
    qstn = _child(var, "qstn")

    missing_values: list[str] = []
    invalrng = _child(var, "invalrng")
    if invalrng is not None:
        for item in _children(invalrng, "item"):
            value = item.get("VALUE") or item.get("value")
            if value is not None:
                missing_values.append(value)

    value_labels: dict[str, str] = {}
    freq: dict[str, int] = {}
    categories = _children(var, "catgry")
    for catgry in categories:
        value = _text(_child(catgry, "catValu"))
        label = _text(_child(catgry, "labl"))
        if value is None:
            continue
        if label is not None:
            value_labels[value] = label
        if catgry.get("missing", "").lower() in {"y", "yes", "true"}:
            missing_values.append(value)
        if include_summary_stats:
            for cat_stat in _children(catgry, "catStat"):
                if cat_stat.get("type") != "freq":
                    continue
                text = _text(cat_stat)
                if text is not None:
                    try:
                        freq[value] = int(float(text))
                    except ValueError:
                        pass

    # Dataverse writes each variable's UNF fingerprint as a <notes> element;
    # split it out so `notes` only carries human-written documentation.
    notes: list[str] = []
    unf: str | None = None
    for note in _children(var, "notes"):
        text = _text(note)
        if text is None:
            continue
        if (note.get("type") or "").upper() == "VDC:UNF":
            unf = text
        else:
            notes.append(text)

    var_id = var.get("ID") or var.get("id")
    entry: dict[str, Any] = {
        "id": var_id,
        "name": var.get("name"),
        "label": _text(_child(var, "labl")),
        "type": (var_format.get("type") if var_format is not None else None),
        "format": (var_format.get("formatname") if var_format is not None else None),
        "question_text": _text(_child(qstn, "qstnLit")) if qstn is not None else None,
        "universe": _text(_child(var, "universe")),
        "missing_values": list(dict.fromkeys(missing_values)),
        "value_labels": value_labels,
        "categorical": bool(categories),
        "interval": var.get("intrvl"),
        "is_weight": (var.get("wgt") or "").lower() == "wgt",
        "notes": notes,
        "unf": unf,
        "groups": groups.get(var_id or "", []),
    }

    if include_summary_stats:
        stats: dict[str, Any] = {}
        for sum_stat in _children(var, "sumStat"):
            stat_type = sum_stat.get("type")
            text = _text(sum_stat)
            if not stat_type or text is None:
                continue
            stats[_STAT_KEY_MAP.get(stat_type, stat_type)] = _number(text)
        if freq:
            stats["freq"] = freq
        entry["summary_stats"] = stats

    return entry
