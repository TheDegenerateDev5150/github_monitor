"""Tests for nullable GitHub profile field change detection."""


# Confirms removing a populated nullable field is reported as a change
def test_nullable_field_removal_is_detected(gm_module):
    unavailable = object()
    assert gm_module.has_nullable_profile_field_changed(None, "Old value", unavailable)


# Confirms adding a previously empty nullable field is reported as a change
def test_nullable_field_addition_is_detected(gm_module):
    unavailable = object()
    assert gm_module.has_nullable_profile_field_changed("New value", None, unavailable)


# Confirms unchanged nullable values remain quiet
def test_unchanged_nullable_field_is_ignored(gm_module):
    unavailable = object()
    assert not gm_module.has_nullable_profile_field_changed(None, None, unavailable)
    assert not gm_module.has_nullable_profile_field_changed("Same", "Same", unavailable)


# Confirms API failures remain distinct from valid null values
def test_unavailable_nullable_field_is_ignored(gm_module):
    unavailable = object()
    assert not gm_module.has_nullable_profile_field_changed(unavailable, "Old value", unavailable)
