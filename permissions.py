# Role names in DB must match keys (e.g. "Financial Analyst").
ROLE_PERMISSIONS = {
    "Admin": ["all"],
    "Financial Analyst": ["upload", "edit", "delete", "view", "review"],
    "Analyst": ["upload", "edit", "delete", "view", "review"],
    "Auditor": ["review", "view"],
    "Client": ["view"],
}
