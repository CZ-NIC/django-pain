"""django-pain LDAP functions."""


def clean_user_data(model_fields):
    """Transform the user data loaded from LDAP into a form suitable for creating a user."""
    model_fields['is_staff'] = True
    return model_fields
