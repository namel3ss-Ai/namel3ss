from __future__ import annotations

ACTION_INGESTION_RUN = "ingestion.run"
ACTION_INGESTION_REVIEW = "ingestion.review"
ACTION_INGESTION_OVERRIDE = "ingestion.override"
ACTION_INGESTION_SKIP = "ingestion.skip"
ACTION_RETRIEVAL_INCLUDE_WARN = "retrieval.include_warn"
ACTION_UPLOAD_REPLACE = "upload.replace"

POLICY_ACTION_TABLE = {
    ACTION_INGESTION_RUN: ("ingestion", "run"),
    ACTION_INGESTION_REVIEW: ("ingestion", "review"),
    ACTION_INGESTION_OVERRIDE: ("ingestion", "override"),
    ACTION_INGESTION_SKIP: ("ingestion", "skip"),
    ACTION_RETRIEVAL_INCLUDE_WARN: ("retrieval", "include_warn"),
    ACTION_UPLOAD_REPLACE: ("upload", "replace"),
}

POLICY_ACTION_LABELS = {
    ACTION_INGESTION_RUN: "Ingestion run",
    ACTION_INGESTION_REVIEW: "Ingestion review",
    ACTION_INGESTION_OVERRIDE: "Ingestion override",
    ACTION_INGESTION_SKIP: "Ingestion skip",
    ACTION_RETRIEVAL_INCLUDE_WARN: "Warn retrieval",
    ACTION_UPLOAD_REPLACE: "Upload replace",
}

POLICY_SECTION_KEYS = {
    "ingestion": {
        "run": ACTION_INGESTION_RUN,
        "review": ACTION_INGESTION_REVIEW,
        "override": ACTION_INGESTION_OVERRIDE,
        "skip": ACTION_INGESTION_SKIP,
    },
    "retrieval": {
        "include_warn": ACTION_RETRIEVAL_INCLUDE_WARN,
    },
    "upload": {
        "replace": ACTION_UPLOAD_REPLACE,
    },
}

POLICY_ACTIONS = tuple(POLICY_ACTION_TABLE.keys())

__all__ = [
    "ACTION_INGESTION_OVERRIDE",
    "ACTION_INGESTION_REVIEW",
    "ACTION_INGESTION_RUN",
    "ACTION_INGESTION_SKIP",
    "ACTION_RETRIEVAL_INCLUDE_WARN",
    "ACTION_UPLOAD_REPLACE",
    "POLICY_ACTIONS",
    "POLICY_ACTION_LABELS",
    "POLICY_ACTION_TABLE",
    "POLICY_SECTION_KEYS",
]
