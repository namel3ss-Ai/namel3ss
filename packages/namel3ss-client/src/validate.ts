import schemaCatalog from "./runtime_contract_schema.json";
import type { ContractWarning } from "./types";

type SchemaField = {
  name: string;
  type: string;
  required: boolean;
  ref?: string;
  item_type?: string;
  item_ref?: string;
};

type SchemaDefinition = {
  fields: SchemaField[];
  additional_fields: boolean;
};

type SchemaMap = Record<string, SchemaDefinition>;

const SCHEMAS: SchemaMap = (schemaCatalog as { schemas: SchemaMap }).schemas;

export function validatePayload(payload: unknown, schemaName: string): ContractWarning[] {
  const schema = SCHEMAS[schemaName];
  if (!schema) {
    return [{ code: "schema.unknown", path: "$", message: `Unknown contract schema '${schemaName}'.` }];
  }
  const warnings: ContractWarning[] = [];
  validateValue(payload, schema, "$", warnings);
  return warnings;
}

export function validateHeadlessUiResponse(payload: unknown): ContractWarning[] {
  return validatePayload(payload, "headless_ui_response");
}

export function validateHeadlessActionResponse(payload: unknown): ContractWarning[] {
  return validatePayload(payload, "headless_action_response");
}

function validateValue(value: unknown, schema: SchemaDefinition, path: string, warnings: ContractWarning[]): void {
  if (!isObject(value)) {
    warnings.push({
      code: "schema.type_mismatch",
      path,
      message: "Expected object payload.",
      expected: "object",
      actual: typeName(value),
    });
    return;
  }
  for (const field of schema.fields) {
    const fieldPath = `${path}.${field.name}`;
    if (!(field.name in value)) {
      if (field.required) {
        warnings.push({
          code: "schema.missing_field",
          path: fieldPath,
          message: `Missing required field '${field.name}'.`,
          expected: field.type,
          actual: "missing",
        });
      }
      continue;
    }
    const fieldValue = value[field.name as keyof typeof value];
    validateField(fieldValue, field, fieldPath, warnings);
  }
  if (!schema.additional_fields) {
    const allowed = new Set(schema.fields.map((entry) => entry.name));
    const unknown = Object.keys(value).filter((entry) => !allowed.has(entry)).sort();
    for (const key of unknown) {
      warnings.push({
        code: "schema.unknown_field",
        path: `${path}.${key}`,
        message: `Unknown field '${key}'.`,
      });
    }
  }
}

function validateField(value: unknown, field: SchemaField, path: string, warnings: ContractWarning[]): void {
  if (!matchesType(value, field.type)) {
    warnings.push({
      code: "schema.type_mismatch",
      path,
      message: `Expected '${field.type}' for '${field.name}'.`,
      expected: field.type,
      actual: typeName(value),
    });
    return;
  }
  if (field.ref && isObject(value)) {
    const schema = SCHEMAS[field.ref];
    if (!schema) {
      warnings.push({
        code: "schema.bad_ref",
        path,
        message: `Unknown schema ref '${field.ref}'.`,
      });
      return;
    }
    validateValue(value, schema, path, warnings);
    return;
  }
  if (field.type !== "array" || !Array.isArray(value)) return;
  for (let index = 0; index < value.length; index += 1) {
    const item = value[index];
    const itemPath = `${path}[${index}]`;
    if (field.item_ref) {
      const schema = SCHEMAS[field.item_ref];
      if (!schema) {
        warnings.push({
          code: "schema.bad_ref",
          path: itemPath,
          message: `Unknown schema ref '${field.item_ref}'.`,
        });
        continue;
      }
      validateValue(item, schema, itemPath, warnings);
      continue;
    }
    if (field.item_type && !matchesType(item, field.item_type)) {
      warnings.push({
        code: "schema.type_mismatch",
        path: itemPath,
        message: `Expected array item type '${field.item_type}'.`,
        expected: field.item_type,
        actual: typeName(item),
      });
    }
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function matchesType(value: unknown, typeNameValue: string): boolean {
  if (typeNameValue === "any") return true;
  if (typeNameValue === "string") return typeof value === "string";
  if (typeNameValue === "boolean") return typeof value === "boolean";
  if (typeNameValue === "number") return typeof value === "number";
  if (typeNameValue === "object") return isObject(value);
  if (typeNameValue === "array") return Array.isArray(value);
  return false;
}

function typeName(value: unknown): string {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value;
}
