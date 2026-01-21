from tests.conftest import parse_program


def _field_signature(identity):
    return [
        (field.name, field.type_name, field.constraint.kind if field.constraint else None)
        for field in identity.fields
    ]


def test_identity_fields_block_matches_legacy():
    block_source = '''identity "user":
  fields:
    subject is text must be present
    email is text must be present
  trust_level is one of "guest", "member"
'''
    legacy_source = '''identity "user":
  field "subject" is text must be present
  field "email" is text must be present
  trust_level is one of ["guest", "member"]
'''
    block_identity = parse_program(block_source).identity
    legacy_identity = parse_program(legacy_source).identity
    assert _field_signature(block_identity) == _field_signature(legacy_identity)
    assert block_identity.trust_levels == legacy_identity.trust_levels


def test_identity_fields_block_allows_quoted_names():
    source = '''identity "user":
  fields:
    "to" is text
'''
    identity = parse_program(source).identity
    assert [field.name for field in identity.fields] == ["to"]
