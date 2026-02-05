# Guardrails API Reference

## Base Classes

### Guardrail

Base class for all guardrail filters and validators.

#### Methods

##### `check(content)` → `GuardrailResult`

Check if content violates this guardrail.

```python
result = guardrail.check(content)
if not result.is_safe:
    print("Violations found")
```

##### `filter(content)` → `str`

Filter content by removing or replacing violations.

```python
filtered = guardrail.filter(content)
```

##### `enable()` → `None`

Enable this guardrail.

```python
guardrail.enable()
```

##### `disable()` → `None`

Disable this guardrail.

```python
guardrail.disable()
```

#### Properties

##### `rule_id` → `str`

Get the rule identifier.

##### `severity` → `GuardrailSeverity`

Get the violation severity level.

##### `enabled` → `bool`

Check if this guardrail is enabled.

### GuardrailResult

Result of applying a guardrail to content.

#### Properties

##### `is_safe` → `bool`

Whether content passed all checks.

##### `violations` → `list[GuardrailViolation]`

List of violations found.

##### `filtered_content` → `str | None`

Filtered version of content (if applicable).

##### `metadata` → `dict`

Additional metadata about the check.

#### Methods

##### `safe(content=None)` → `GuardrailResult` (classmethod)

Create a safe result.

```python
result = GuardrailResult.safe(content)
```

##### `violated(violations, filtered_content=None)` → `GuardrailResult` (classmethod)

Create a violated result.

```python
result = GuardrailResult.violated(violations_list, filtered)
```

### GuardrailViolation

Represents a single guardrail rule violation.

#### Properties

##### `rule_id` → `str`

Rule identifier.

##### `message` → `str`

Violation message.

##### `severity` → `GuardrailSeverity`

Severity level.

##### `matched_text` → `str | None`

Text that matched the violation pattern.

##### `metadata` → `dict`

Additional violation metadata.

#### Methods

##### `to_dict()` → `dict`

Convert violation to dictionary.

## Filter Implementations

### KeywordFilter

Filters content based on keyword matches.

#### Parameters

- `rule_id` (str): Unique identifier
- `keywords` (list[str]): List of keywords to filter
- `severity` (GuardrailSeverity): Severity for violations
- `case_sensitive` (bool): Whether matching is case sensitive
- `match_substring` (bool): Match anywhere or whole words
- `replacement` (str | None): Replacement string for filtering

#### Example

```python
filter = KeywordFilter(
    rule_id="no-api-keys",
    keywords=["sk-", "Bearer"],
    severity=GuardrailSeverity.CRITICAL,
)
```

### RegexFilter

Filters content using regular expressions.

#### Parameters

- `rule_id` (str): Unique identifier
- `pattern` (str): Regular expression pattern
- `severity` (GuardrailSeverity): Severity for violations
- `flags` (int): Regex flags
- `replacement` (str | None): Replacement string
- `message` (str | None): Custom violation message

#### Example

```python
filter = RegexFilter(
    rule_id="api-keys",
    pattern=r"sk-[a-zA-Z0-9]{32}",
    severity=GuardrailSeverity.CRITICAL,
)
```

### LengthFilter

Filters content based on length constraints.

#### Parameters

- `rule_id` (str): Unique identifier
- `min_length` (int | None): Minimum allowed length
- `max_length` (int | None): Maximum allowed length
- `severity` (GuardrailSeverity): Severity for violations
- `count_mode` (str): How to count ("chars", "words", "tokens_chars", "tokens_words")

#### Example

```python
filter = LengthFilter(
    rule_id="length",
    min_length=1,
    max_length=1000,
    count_mode="chars",
)
```

### ProfanityFilter

Filters profanity and inappropriate language.

#### Parameters

- `rule_id` (str): Unique identifier
- `severity` (GuardrailSeverity): Severity for violations
- `profanity_list` (list[str] | None): Custom profanity word list
- `case_sensitive` (bool): Whether matching is case sensitive
- `replacement` (str | None): Replacement string

#### Example

```python
filter = ProfanityFilter(
    rule_id="no-profanity",
    severity=GuardrailSeverity.WARNING,
)
```

### UrlFilter

Filters or detects URLs in content.

#### Parameters

- `rule_id` (str): Unique identifier
- `action` (str): "block" (deny all), "allow" (allow allowed_domains), "deny" (deny blocked_domains)
- `severity` (GuardrailSeverity): Severity for violations
- `allowed_domains` (list[str] | None): List of allowed domains
- `blocked_domains` (list[str] | None): List of blocked domains

#### Example

```python
filter = UrlFilter(
    rule_id="block-urls",
    action="block",
    severity=GuardrailSeverity.INFO,
)
```

### EmailFilter

Filters or detects email addresses in content.

#### Parameters

- `rule_id` (str): Unique identifier
- `action` (str): "block", "allow", or "deny"
- `severity` (GuardrailSeverity): Severity for violations
- `allowed_domains` (list[str] | None): List of allowed email domains
- `blocked_domains` (list[str] | None): List of blocked email domains
- `replacement` (str | None): Replacement string

#### Example

```python
filter = EmailFilter(
    rule_id="no-emails",
    action="block",
    severity=GuardrailSeverity.INFO,
)
```

## Composite Guardrails

### CompositeGuardrail

Combines multiple guardrails into a single check.

#### Parameters

- `rule_id` (str): Unique identifier
- `guardrails` (list[Guardrail]): List of guardrails to compose
- `severity` (GuardrailSeverity): Default severity
- `stop_on_first` (bool): Stop after first violation or check all

#### Methods

##### `add_guardrail(guardrail)` → `None`

Add a guardrail to the composite.

##### `remove_guardrail(rule_id)` → `bool`

Remove a guardrail by rule ID returns True if removed.

#### Example

```python
composite = CompositeGuardrail(
    rule_id="composite-check",
    guardrails=[filter1, filter2],
    stop_on_first=False,
)
```

### ConditionalGuardrail

Applies a guardrail only when a condition is met.

#### Parameters

- `rule_id` (str): Unique identifier
- `guardrail` (Guardrail): Guardrail to apply conditionally
- `condition` (Callable[[dict], bool]): Function that takes context and returns bool
- `severity` (GuardrailSeverity): Severity for violations

#### Methods

##### `set_context(context)` → `None`

Set the context for condition evaluation.

#### Example

```python
guardrail = ConditionalGuardrail(
    rule_id="production-only",
    guardrail=filter,
    condition=lambda ctx: ctx.get("mode") == "production",
)
guardrail.set_context({"mode": "production"})
```

## Validators

### ContentValidator

High-level content validator with pre-configured guardrails.

#### Methods

##### `check(content)` → `GuardrailResult`

Check content against all guardrails.

##### `filter(content)` → `str`

Filter content by applying all guardrails.

##### `add_guardrail(guardrail)` → `None`

Add a guardrail to the validator.

##### `remove_guardrail(rule_id)` → `bool`

Remove a guardrail by rule ID returns True if removed.

#### Class Methods

##### `create_input_validator(severity=GuardrailSeverity.WARNING)` → `ContentValidator`

Create a validator for user input.

##### `create_output_validator(severity=GuardrailSeverity.WARNING)` → `ContentValidator`

Create a validator for AI model output.

##### `create_pii_validator(severity=GuardrailSeverity.CRITICAL)` → `ContentValidator`

Create a validator focusing on PII detection.

##### `create_custom_validator(forbidden_keywords=None, allowed_domains=None, max_length=None, severity=GuardrailSeverity.WARNING)` → `ContentValidator`

Create a custom validator with specific rules.

##### `create_code_validator(severity=GuardrailSeverity.INFO)` → `ContentValidator`

Create a validator for code snippets (less strict).

### SafetyValidator

Validator focused specifically on content safety.

#### Parameters

- `severity` (GuardrailSeverity): Severity level
- `block_self_harm` (bool): Block self-harm related content
- `block_harmful` (bool): Block harmful content
- `block_profane` (bool): Block profane content

### ComplianceValidator

Validator for regulatory compliance.

#### Parameters

- `gdpr_mode` (bool): Enable GDPR compliance (detect PII)
- `hipaa_mode` (bool): Enable HIPAA compliance (detect PHI)
- `severity` (GuardrailSeverity): Severity level

## Enums

### GuardrailSeverity

Severity levels for guardrail violations.

- `INFO`: Informational only
- `WARNING`: Warning (may need attention)
- `ERROR`: Error (should be addressed)
- `CRITICAL`: Critical (must block)

#### Example

```python
from ai_lib_python.guardrails import GuardrailSeverity

severity = GuardrailSeverity.CRITICAL
```
