"""PII masking utilities for audit output and logging.

Minimises personally identifiable information in logs while keeping
enough context for debugging. Applied to final output and audit trail.
"""



def mask_email(email: str) -> str:
    """Mask an email address: 'john.doe@example.com' → 'j***@example.com'."""
    if not email or "@" not in email:
        return email
    local, domain = email.rsplit("@", 1)
    return f"{local[0]}***@{domain}"


def mask_name(name: str) -> str:
    """Mask a name: 'Maria Gonzalez' → 'Maria G.'."""
    if not name:
        return name
    parts = name.split()
    if len(parts) <= 1:
        return name
    return f"{parts[0]} {parts[-1][0]}."


def mask_customer_profile(profile: dict) -> dict:
    """Return a copy of the profile with PII masked."""
    if not profile or not isinstance(profile, dict):
        return profile

    masked = dict(profile)
    if "email" in masked:
        masked["email"] = mask_email(masked["email"])
    if "name" in masked:
        masked["name"] = mask_name(masked["name"])
    return masked


def mask_customer_context(context: dict) -> dict:
    """Mask PII in the full customer context dict."""
    if not context or not isinstance(context, dict):
        return context
    if "error" in context:
        return context

    masked = dict(context)
    if "profile" in masked:
        masked["profile"] = mask_customer_profile(masked["profile"])
    return masked
