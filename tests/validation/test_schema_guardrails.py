from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.schema.records import (
    EXPIRES_AT_FIELD,
    SYSTEM_FIELDS,
    TENANT_KEY_FIELD,
    FieldSchema,
    RecordSchema,
)


class TestDuplicateFieldNames:

    def test_duplicate_field_name_raises_error(self) -> None:
        with pytest.raises(Namel3ssError) as exc:
            RecordSchema(
                name="Order",
                fields=[
                    FieldSchema(name="item", type_name="text"),
                    FieldSchema(name="item", type_name="text"),
                ],
            )
        err = exc.value
        assert "Duplicate field" in err.message
        assert "'item'" in err.message
        assert "'Order'" in err.message

    def test_duplicate_field_name_different_types_raises_error(self) -> None:
        with pytest.raises(Namel3ssError) as exc:
            RecordSchema(
                name="Product",
                fields=[
                    FieldSchema(name="value", type_name="text"),
                    FieldSchema(name="value", type_name="number"),
                ],
            )
        err = exc.value
        assert "Duplicate field" in err.message
        assert "'value'" in err.message
        assert "'Product'" in err.message

    def test_multiple_unique_fields_allowed(self) -> None:
        schema = RecordSchema(
            name="User",
            fields=[
                FieldSchema(name="email", type_name="text"),
                FieldSchema(name="username", type_name="text"),
                FieldSchema(name="id", type_name="number"),
            ],
        )
        assert len(schema.fields) == 3
        assert set(schema.field_map.keys()) == {"email", "username", "id"}

    def test_first_duplicate_is_reported(self) -> None:
        with pytest.raises(Namel3ssError) as exc:
            RecordSchema(
                name="Task",
                fields=[
                    FieldSchema(name="status", type_name="text"),
                    FieldSchema(name="priority", type_name="number"),
                    FieldSchema(name="status", type_name="text"),
                ],
            )
        err = exc.value
        assert "'status'" in err.message
        assert "'Task'" in err.message


class TestReservedSystemFields:

    def test_tenant_key_field_is_reserved(self) -> None:
        with pytest.raises(Namel3ssError) as exc:
            RecordSchema(
                name="Account",
                fields=[
                    FieldSchema(name=TENANT_KEY_FIELD, type_name="text"),
                ],
            )
        err = exc.value
        assert "reserved" in err.message.lower()
        assert f"'{TENANT_KEY_FIELD}'" in err.message
        assert "'Account'" in err.message

    def test_expires_at_field_is_reserved(self) -> None:
        with pytest.raises(Namel3ssError) as exc:
            RecordSchema(
                name="Session",
                fields=[
                    FieldSchema(name=EXPIRES_AT_FIELD, type_name="number"),
                ],
            )
        err = exc.value
        assert "reserved" in err.message.lower()
        assert f"'{EXPIRES_AT_FIELD}'" in err.message
        assert "'Session'" in err.message

    def test_all_system_fields_are_reserved(self) -> None:
        for system_field in SYSTEM_FIELDS:
            with pytest.raises(Namel3ssError) as exc:
                RecordSchema(
                    name="TestRecord",
                    fields=[
                        FieldSchema(name=system_field, type_name="text"),
                    ],
                )
            err = exc.value
            assert "reserved" in err.message.lower()
            assert f"'{system_field}'" in err.message

    def test_system_fields_added_automatically_for_tenant_key(self) -> None:
        schema = RecordSchema(
            name="TenantData",
            fields=[FieldSchema(name="value", type_name="text")],
            tenant_key=["org_id"],
        )
        system_names = {f.name for f in schema.system_fields}
        assert TENANT_KEY_FIELD in system_names

    def test_system_fields_added_automatically_for_ttl(self) -> None:
        from decimal import Decimal

        schema = RecordSchema(
            name="EphemeralData",
            fields=[FieldSchema(name="data", type_name="text")],
            ttl_hours=Decimal("24"),
        )
        system_names = {f.name for f in schema.system_fields}
        assert EXPIRES_AT_FIELD in system_names

    def test_reserved_field_among_valid_fields_raises_error(self) -> None:
        with pytest.raises(Namel3ssError) as exc:
            RecordSchema(
                name="MixedRecord",
                fields=[
                    FieldSchema(name="name", type_name="text"),
                    FieldSchema(name=TENANT_KEY_FIELD, type_name="text"),
                    FieldSchema(name="age", type_name="number"),
                ],
            )
        err = exc.value
        assert "reserved" in err.message.lower()
        assert TENANT_KEY_FIELD in err.message


class TestStructuredErrorFields:

    def test_duplicate_field_error_message_format_is_stable(self) -> None:
        with pytest.raises(Namel3ssError) as exc:
            RecordSchema(
                name="Invoice",
                fields=[
                    FieldSchema(name="amount", type_name="number"),
                    FieldSchema(name="amount", type_name="number"),
                ],
            )
        err = exc.value
        assert err.message.startswith("Duplicate field")
        assert "'amount'" in err.message
        assert "in record" in err.message
        assert "'Invoice'" in err.message

    def test_reserved_field_error_message_format_is_stable(self) -> None:
        with pytest.raises(Namel3ssError) as exc:
            RecordSchema(
                name="Tenant",
                fields=[
                    FieldSchema(name=TENANT_KEY_FIELD, type_name="text"),
                ],
            )
        err = exc.value
        assert err.message.startswith("Field")
        assert f"'{TENANT_KEY_FIELD}'" in err.message
        assert "reserved" in err.message.lower()
        assert "'Tenant'" in err.message

    def test_unsupported_type_error_message_format_is_stable(self) -> None:
        with pytest.raises(Namel3ssError) as exc:
            RecordSchema(
                name="BadRecord",
                fields=[
                    FieldSchema(name="data", type_name="unknown_type"),
                ],
            )
        err = exc.value
        assert "Unsupported field type" in err.message
        assert "'unknown_type'" in err.message
        assert "'BadRecord'" in err.message

    def test_error_is_namel3ss_error_type(self) -> None:
        with pytest.raises(Namel3ssError):
            RecordSchema(
                name="Dup",
                fields=[
                    FieldSchema(name="x", type_name="text"),
                    FieldSchema(name="x", type_name="text"),
                ],
            )

        with pytest.raises(Namel3ssError):
            RecordSchema(
                name="Reserved",
                fields=[
                    FieldSchema(name=TENANT_KEY_FIELD, type_name="text"),
                ],
            )

        with pytest.raises(Namel3ssError):
            RecordSchema(
                name="BadType",
                fields=[
                    FieldSchema(name="f", type_name="invalid"),
                ],
            )


class TestValidSchemas:

    def test_empty_fields_allowed(self) -> None:
        schema = RecordSchema(name="EmptyRecord", fields=[])
        assert schema.name == "EmptyRecord"
        assert len(schema.fields) == 0

    def test_single_field_schema(self) -> None:
        schema = RecordSchema(
            name="Simple",
            fields=[FieldSchema(name="value", type_name="text")],
        )
        assert schema.name == "Simple"
        assert len(schema.fields) == 1
        assert schema.field_map["value"].type_name == "text"

    def test_all_supported_types(self) -> None:
        supported = [
            "text",
            "string",
            "str",
            "number",
            "int",
            "integer",
            "boolean",
            "bool",
            "json",
            "list",
            "map",
        ]
        fields = [
            FieldSchema(name=f"field_{i}", type_name=t) for i, t in enumerate(supported)
        ]
        schema = RecordSchema(name="AllTypes", fields=fields)
        assert len(schema.fields) == len(supported)
