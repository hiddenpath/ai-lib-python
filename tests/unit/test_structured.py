"""Tests for structured output module."""

import json

import pytest
from pydantic import BaseModel

from ai_lib_python.structured import (
    JsonMode,
    JsonModeConfig,
    OutputValidator,
    SchemaGenerator,
    StructuredOutput,
    ValidationResult,
    json_schema_from_type,
)
from ai_lib_python.structured.json_mode import extract_json


class TestJsonSchemaFromType:
    """Tests for json_schema_from_type."""

    def test_basic_types(self) -> None:
        """Test basic type conversion."""
        assert json_schema_from_type(str) == {"type": "string"}
        assert json_schema_from_type(int) == {"type": "integer"}
        assert json_schema_from_type(float) == {"type": "number"}
        assert json_schema_from_type(bool) == {"type": "boolean"}

    def test_list_type(self) -> None:
        """Test list type conversion."""
        schema = json_schema_from_type(list[int])
        assert schema["type"] == "array"
        assert schema["items"]["type"] == "integer"

    def test_dict_type(self) -> None:
        """Test dict type conversion."""
        schema = json_schema_from_type(dict[str, int])
        assert schema["type"] == "object"
        assert schema["additionalProperties"]["type"] == "integer"

    def test_none_type(self) -> None:
        """Test None type."""
        assert json_schema_from_type(type(None)) == {"type": "null"}


class TestSchemaGenerator:
    """Tests for SchemaGenerator."""

    def test_basic_schema(self) -> None:
        """Test basic schema generation."""
        gen = SchemaGenerator(title="User")
        gen.add_property("name", str, description="User's name")
        gen.add_property("age", int, minimum=0)

        schema = gen.build()
        assert schema["title"] == "User"
        assert "name" in schema["properties"]
        assert schema["properties"]["age"]["minimum"] == 0
        assert "name" in schema["required"]

    def test_optional_property(self) -> None:
        """Test optional property."""
        gen = SchemaGenerator()
        gen.add_property("optional_field", str, required=False)

        schema = gen.build()
        assert "optional_field" not in schema.get("required", [])

    def test_enum_constraint(self) -> None:
        """Test enum constraint."""
        gen = SchemaGenerator()
        gen.add_property("status", str, enum=["active", "inactive"])

        schema = gen.build()
        assert schema["properties"]["status"]["enum"] == ["active", "inactive"]

    def test_string_constraints(self) -> None:
        """Test string constraints."""
        gen = SchemaGenerator()
        gen.add_property(
            "username",
            str,
            min_length=3,
            max_length=20,
            pattern=r"^[a-z]+$",
        )

        schema = gen.build()
        props = schema["properties"]["username"]
        assert props["minLength"] == 3
        assert props["maxLength"] == 20
        assert props["pattern"] == r"^[a-z]+$"

    def test_to_json(self) -> None:
        """Test JSON serialization."""
        gen = SchemaGenerator()
        gen.add_property("field", str)

        json_str = gen.to_json()
        parsed = json.loads(json_str)
        assert "properties" in parsed


class TestOutputValidator:
    """Tests for OutputValidator."""

    def test_validate_json_string(self) -> None:
        """Test validating JSON string."""
        validator = OutputValidator()
        result = validator.validate('{"name": "test"}')
        assert result.valid
        assert result.data == {"name": "test"}

    def test_validate_invalid_json(self) -> None:
        """Test validating invalid JSON."""
        validator = OutputValidator()
        result = validator.validate("not json")
        assert not result.valid
        assert "Invalid JSON" in result.errors[0]

    def test_validate_dict(self) -> None:
        """Test validating dictionary."""
        validator = OutputValidator()
        result = validator.validate({"name": "test"})
        assert result.valid

    def test_validate_with_pydantic(self) -> None:
        """Test validating with Pydantic model."""

        class User(BaseModel):
            name: str
            age: int

        validator = OutputValidator(User)
        result = validator.validate({"name": "Alice", "age": 30})
        assert result.valid
        assert isinstance(result.data, User)
        assert result.data.name == "Alice"

    def test_validate_pydantic_failure(self) -> None:
        """Test Pydantic validation failure."""

        class User(BaseModel):
            name: str
            age: int

        validator = OutputValidator(User)
        result = validator.validate({"name": "Alice", "age": "not_an_int"})
        assert not result.valid

    def test_validate_json_schema(self) -> None:
        """Test validating with JSON schema."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer", "minimum": 0},
            },
            "required": ["name"],
        }
        validator = OutputValidator(schema)

        # Valid data
        result = validator.validate({"name": "test", "count": 5})
        assert result.valid

        # Missing required
        result = validator.validate({"count": 5})
        assert not result.valid
        assert "Missing required" in result.errors[0]

    def test_validate_or_raise(self) -> None:
        """Test validate_or_raise."""
        validator = OutputValidator()

        # Valid - should return data
        data = validator.validate_or_raise('{"name": "test"}')
        assert data == {"name": "test"}

        # Invalid - should raise
        from ai_lib_python.structured.validator import ValidationError

        with pytest.raises(ValidationError):
            validator.validate_or_raise("invalid json")

    def test_parse_into_model(self) -> None:
        """Test parsing into Pydantic model."""

        class User(BaseModel):
            name: str

        validator = OutputValidator()
        user = validator.parse('{"name": "Alice"}', User)
        assert user.name == "Alice"


class TestJsonModeConfig:
    """Tests for JsonModeConfig."""

    def test_json_object_mode(self) -> None:
        """Test JSON object mode config."""
        config = JsonModeConfig.json_object()
        assert config.mode == JsonMode.JSON
        format_dict = config.to_openai_format()
        assert format_dict["response_format"]["type"] == "json_object"

    def test_from_schema(self) -> None:
        """Test creating from schema."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        config = JsonModeConfig.from_schema(schema, name="user")
        assert config.mode == JsonMode.JSON_SCHEMA
        assert config.schema_name == "user"

    def test_from_pydantic(self) -> None:
        """Test creating from Pydantic model."""

        class User(BaseModel):
            name: str

        config = JsonModeConfig.from_pydantic(User)
        assert config.mode == JsonMode.JSON_SCHEMA
        assert config.schema_name == "User"

    def test_to_openai_format_json_schema(self) -> None:
        """Test OpenAI format for JSON schema mode."""
        schema = {"type": "object"}
        config = JsonModeConfig.from_schema(schema, name="test")
        format_dict = config.to_openai_format()
        assert format_dict["response_format"]["type"] == "json_schema"
        assert format_dict["response_format"]["json_schema"]["name"] == "test"

    def test_off_mode(self) -> None:
        """Test OFF mode."""
        config = JsonModeConfig(mode=JsonMode.OFF)
        assert config.to_openai_format() == {}


class TestStructuredOutput:
    """Tests for StructuredOutput."""

    def test_from_response_valid_json(self) -> None:
        """Test creating from valid JSON response."""
        output = StructuredOutput.from_response('{"name": "test"}')
        assert output.is_valid
        assert output.parsed == {"name": "test"}

    def test_from_response_invalid_json(self) -> None:
        """Test creating from invalid JSON response."""
        output = StructuredOutput.from_response("not json")
        assert output.raw == "not json"
        assert output.parsed is None

    def test_from_response_with_validator(self) -> None:
        """Test creating with validator."""

        class User(BaseModel):
            name: str

        validator = OutputValidator(User)
        output = StructuredOutput.from_response('{"name": "Alice"}', validator)
        assert output.is_valid
        assert isinstance(output.validated, User)

    def test_as_model(self) -> None:
        """Test getting output as model."""

        class User(BaseModel):
            name: str

        output = StructuredOutput(
            raw='{"name": "Alice"}',
            parsed={"name": "Alice"},
            validation_result=ValidationResult(valid=True),
        )
        user = output.as_model(User)
        assert user.name == "Alice"


class TestExtractJson:
    """Tests for extract_json function."""

    def test_direct_json(self) -> None:
        """Test extracting direct JSON."""
        result = extract_json('{"name": "test"}')
        assert result == {"name": "test"}

    def test_from_markdown_code_block(self) -> None:
        """Test extracting from markdown code block."""
        text = """Here is the data:
```json
{"name": "test"}
```
"""
        result = extract_json(text)
        assert result == {"name": "test"}

    def test_from_plain_code_block(self) -> None:
        """Test extracting from plain code block."""
        text = """
```
{"value": 42}
```
"""
        result = extract_json(text)
        assert result == {"value": 42}

    def test_embedded_json_object(self) -> None:
        """Test extracting embedded JSON object."""
        text = 'Some text {"key": "value"} more text'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_no_json_found(self) -> None:
        """Test when no JSON is found."""
        result = extract_json("Just some text")
        assert result is None
