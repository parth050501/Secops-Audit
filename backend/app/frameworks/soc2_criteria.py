"""
Full SOC 2 Trust Services Criteria (2017, with 2022 points of focus).
Organized by the five Trust Service Categories.
Security (Common Criteria) is mandatory; the other four are optional add-ons.
"""

TRUST_CATEGORIES = {
    "security": {
        "name": "Security (Common Criteria)",
        "mandatory": True,
        "description": "Information and systems are protected against unauthorized access, disclosure, and damage.",
    },
    "availability": {
        "name": "Availability",
        "mandatory": False,
        "description": "Information and systems are available for operation and use as committed or agreed.",
    },
    "confidentiality": {
        "name": "Confidentiality",
        "mandatory": False,
        "description": "Information designated as confidential is protected as committed or agreed.",
    },
    "processing_integrity": {
        "name": "Processing Integrity",
        "mandatory": False,
        "description": "System processing is complete, valid, accurate, timely, and authorized.",
    },
    "privacy": {
        "name": "Privacy",
        "mandatory": False,
        "description": "Personal information is collected, used, retained, disclosed, and disposed of appropriately.",
    },
}

# Full Common Criteria (CC) + category-specific criteria
SOC2_CRITERIA = [
    # ── CC1: Control Environment ──
    {"id":"CC1.1","category":"security","title":"Demonstrates commitment to integrity and ethical values","focus":"governance"},
    {"id":"CC1.2","category":"security","title":"Board exercises oversight responsibility","focus":"governance"},
    {"id":"CC1.3","category":"security","title":"Management establishes structure, authority, and responsibility","focus":"governance"},
    {"id":"CC1.4","category":"security","title":"Demonstrates commitment to competence","focus":"governance"},
    {"id":"CC1.5","category":"security","title":"Enforces accountability","focus":"governance"},
    # ── CC2: Communication and Information ──
    {"id":"CC2.1","category":"security","title":"Obtains/generates relevant quality information","focus":"logging"},
    {"id":"CC2.2","category":"security","title":"Communicates internal control information","focus":"governance"},
    {"id":"CC2.3","category":"security","title":"Communicates with external parties","focus":"governance"},
    # ── CC3: Risk Assessment ──
    {"id":"CC3.1","category":"security","title":"Specifies objectives to identify and assess risk","focus":"risk"},
    {"id":"CC3.2","category":"security","title":"Identifies and analyzes risk","focus":"risk"},
    {"id":"CC3.3","category":"security","title":"Considers potential for fraud","focus":"risk"},
    {"id":"CC3.4","category":"security","title":"Identifies and assesses changes","focus":"config"},
    # ── CC4: Monitoring Activities ──
    {"id":"CC4.1","category":"security","title":"Selects/develops ongoing evaluations","focus":"logging"},
    {"id":"CC4.2","category":"security","title":"Evaluates and communicates deficiencies","focus":"logging"},
    # ── CC5: Control Activities ──
    {"id":"CC5.1","category":"security","title":"Selects/develops control activities","focus":"config"},
    {"id":"CC5.2","category":"security","title":"Selects/develops technology controls","focus":"config"},
    {"id":"CC5.3","category":"security","title":"Deploys controls through policies and procedures","focus":"config"},
    # ── CC6: Logical and Physical Access ──
    {"id":"CC6.1","category":"security","title":"Implements logical access security software and infrastructure","focus":"access_control"},
    {"id":"CC6.2","category":"security","title":"Registers and authorizes new users before granting access","focus":"identity"},
    {"id":"CC6.3","category":"security","title":"Removes access upon termination or role change","focus":"identity"},
    {"id":"CC6.4","category":"security","title":"Restricts physical access to facilities","focus":"config"},
    {"id":"CC6.5","category":"security","title":"Discontinues logical/physical protections when no longer needed","focus":"data_protection"},
    {"id":"CC6.6","category":"security","title":"Implements controls to protect against external threats","focus":"network_security"},
    {"id":"CC6.7","category":"security","title":"Restricts transmission, movement, and removal of information","focus":"encryption"},
    {"id":"CC6.8","category":"security","title":"Prevents/detects unauthorized or malicious software","focus":"endpoint"},
    # ── CC7: System Operations ──
    {"id":"CC7.1","category":"security","title":"Detects and monitors configuration changes","focus":"config"},
    {"id":"CC7.2","category":"security","title":"Monitors components for anomalies","focus":"logging"},
    {"id":"CC7.3","category":"security","title":"Evaluates security events and responds","focus":"logging"},
    {"id":"CC7.4","category":"security","title":"Responds to security incidents","focus":"risk"},
    {"id":"CC7.5","category":"security","title":"Recovers from identified security incidents","focus":"availability"},
    # ── CC8: Change Management ──
    {"id":"CC8.1","category":"security","title":"Authorizes, designs, tests, and approves changes","focus":"config"},
    # ── CC9: Risk Mitigation ──
    {"id":"CC9.1","category":"security","title":"Identifies and mitigates business disruption risks","focus":"risk"},
    {"id":"CC9.2","category":"security","title":"Assesses and manages vendor/partner risks","focus":"risk"},
    # ── Availability (A) ──
    {"id":"A1.1","category":"availability","title":"Maintains capacity to meet availability commitments","focus":"availability"},
    {"id":"A1.2","category":"availability","title":"Environmental protections, backup, and recovery","focus":"availability"},
    {"id":"A1.3","category":"availability","title":"Tests recovery plan procedures","focus":"availability"},
    # ── Confidentiality (C) ──
    {"id":"C1.1","category":"confidentiality","title":"Identifies and maintains confidential information","focus":"data_protection"},
    {"id":"C1.2","category":"confidentiality","title":"Disposes of confidential information securely","focus":"data_protection"},
    # ── Processing Integrity (PI) ──
    {"id":"PI1.1","category":"processing_integrity","title":"Obtains/uses relevant information for processing","focus":"logging"},
    {"id":"PI1.2","category":"processing_integrity","title":"Processing inputs are complete and accurate","focus":"config"},
    {"id":"PI1.3","category":"processing_integrity","title":"Processing is complete, accurate, and timely","focus":"config"},
    {"id":"PI1.4","category":"processing_integrity","title":"Outputs are complete, accurate, and timely","focus":"config"},
    {"id":"PI1.5","category":"processing_integrity","title":"Stores inputs/outputs completely and accurately","focus":"data_protection"},
    # ── Privacy (P) ──
    {"id":"P1.1","category":"privacy","title":"Provides notice about privacy practices","focus":"data_protection"},
    {"id":"P2.1","category":"privacy","title":"Communicates choices regarding personal information","focus":"data_protection"},
    {"id":"P3.1","category":"privacy","title":"Collects personal information consistently with objectives","focus":"data_protection"},
    {"id":"P4.1","category":"privacy","title":"Uses/retains personal information per objectives","focus":"data_protection"},
    {"id":"P5.1","category":"privacy","title":"Provides access to personal information","focus":"access_control"},
    {"id":"P6.1","category":"privacy","title":"Discloses personal information per objectives","focus":"data_protection"},
    {"id":"P7.1","category":"privacy","title":"Maintains quality of personal information","focus":"data_protection"},
    {"id":"P8.1","category":"privacy","title":"Monitors and addresses privacy compliance","focus":"logging"},
]


def criteria_for_categories(categories: list) -> list:
    """Return criteria for the selected trust categories (security always included)."""
    cats = set(categories) | {"security"}
    return [c for c in SOC2_CRITERIA if c["category"] in cats]
