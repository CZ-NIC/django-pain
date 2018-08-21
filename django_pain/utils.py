"""Various utils."""


def full_class_name(cls):
    """Return full class name includeing the module path."""
    return "{}.{}".format(cls.__module__, cls.__qualname__)
