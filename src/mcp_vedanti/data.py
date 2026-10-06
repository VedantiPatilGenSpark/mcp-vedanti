"""Synthetic employee records and policy sheets.

Hire dates and issue dates are ISO strings. Callers compute tenure and eligibility.
"""

import datetime

AS_OF = datetime.date(2026, 10, 1)
EARLY_REQUEST_DAYS = 90
CATALOG_ITEMS = ("monitor", "laptop", "dock", "headset")
POLICY_ROLES = ("standard", "manager", "director")

POLICY = {
    "standard": [
        {"item": "monitor", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0},
        {"item": "laptop", "max_count": 1, "refresh_years": 4, "min_tenure_years": 1},
        {"item": "headset", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0},
    ],
    "manager": [
        {"item": "monitor", "max_count": 2, "refresh_years": 3, "min_tenure_years": 0},
        {"item": "laptop", "max_count": 1, "refresh_years": 2, "min_tenure_years": 0},
        {"item": "dock", "max_count": 1, "refresh_years": 4, "min_tenure_years": 0},
        {"item": "headset", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0},
    ],
    "director": [
        {"item": "monitor", "max_count": 2, "refresh_years": 2, "min_tenure_years": 0},
        {"item": "laptop", "max_count": 1, "refresh_years": 2, "min_tenure_years": 0},
        {"item": "dock", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0},
        {"item": "headset", "max_count": 1, "refresh_years": 3, "min_tenure_years": 0},
    ],
}

EMPLOYEES = {
    "E201": {
        "employee_id": "E201",
        "role": "manager",
        "hire_date": "2019-06-01",
        "equipment": [
            {"item": "monitor", "issued_on": "2025-01-01"},
        ],
    },
    "E202": {
        "employee_id": "E202",
        "role": "standard",
        "hire_date": "2018-03-01",
        "equipment": [
            {"item": "monitor", "issued_on": "2023-08-01"},
        ],
    },
    "E203": {
        "employee_id": "E203",
        "role": "standard",
        "hire_date": "2018-03-01",
        "equipment": [
            {"item": "monitor", "issued_on": "2024-01-15"},
        ],
    },
    "E204": {
        "employee_id": "E204",
        "role": "standard",
        "hire_date": "2018-03-01",
        "equipment": [],
    },
    "E205": {
        "employee_id": "E205",
        "role": "standard",
        "hire_date": "2026-04-01",
        "equipment": [],
    },
    "E207": {
        "employee_id": "E207",
        "role": "standard",
        "hire_date": "2018-03-01",
        "equipment": [],
    },
    "E208": {
        "employee_id": "E208",
        "role": "standard",
        "hire_date": "2018-03-01",
        "equipment": [
            {"item": "monitor", "issued_on": "2020-01-01"},
            {"item": "monitor", "issued_on": "2021-06-01"},
        ],
    },
    "E209": {
        "employee_id": "E209",
        "role": "contractor",
        "hire_date": "2018-03-01",
        "equipment": [
            {"item": "monitor", "issued_on": "2022-01-15"},
        ],
    },
    "E210": {
        "employee_id": "E210",
        "role": "standard",
        "hire_date": "2018-03-01",
        "equipment": [
            {"item": "monitor", "issued_on": "2023-11-15"},
        ],
    },
    "E211": {
        "employee_id": "E211",
        "role": "manager",
        "hire_date": "2015-01-01",
        "equipment": [
            {"item": "monitor", "issued_on": "2020-06-01"},
            {"item": "monitor", "issued_on": "2026-06-01"},
        ],
    },
    "E212": {
        "employee_id": "E212",
        "role": "director",
        "hire_date": "2016-05-01",
        "equipment": [],
    },
}
