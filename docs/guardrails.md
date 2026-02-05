# Guardrails: Content Filtering and Safety

The `ai_lib_python.guardrails` module provides a flexible framework for filtering and validating content for safety, compliance, and policy enforcement.

## Overview

Guardrails allow you to:

- Filter user inputs for security and compliance
- Filter AI model outputs for PII and sensitive data
- Enforce content policies (profanity, harmful content)
- Customize rules for your specific use case

## Core Concepts

### Guardrail Rule

A guardrail rule implements content checking logic:

```python
from ai_lib_python.guardrails import KeywordFilter, GuardrailSeverity

filter = KeywordFilter(
    rule_id="no-api-keys",
    keywords=["sk-", "Bearer"],
    severity=GuardrailSeverity.CRITICAL,
    case_sensitive=False,
)

result = filter.check("Here is my API key: sk-12345")

if not result.is_safe:
    print(f"Blocked: {result.violations[0].message}")
```

### Guardrail Result

Every guardrail check returns a `GuardrailResult`:

```python
from ai_lib_python.guardrails import GuardrailResult

result = filter.check(content)

if result.is_safe:
    print("Content is safe")
else:
    print(f"Found {len(result.violations)} violations")
    for v in result.violations:
        print(f"  - {v.message} (severity: {v.severity.value})")
```

### Filtering vs Checking

You can either **check** content (detect violations) or **filter** content (remove violations):

```python
# Check for violations
result = filter.check(content)
if not result.is_safe:
    print("Content violated rules")

# Filter content (remove violations)
filtered = filter.filter(content)
print(filtered)  # Violations replaced with [REDACTED]
```

## Built-in Filters

### KeywordFilter

Filter based on keyword matches:

```python
from ai_lib_python.guardrails import KeywordFilter, GuardrailSeverity

filter = KeywordFilter(
    rule_id="forbidden-words",
    keywords=["password", "secret", "token"],
    severity=GuardrailSeverity.ERROR,
    case_sensitive=False,
    match_substring=True,
)
```

### RegexFilter

Filter using regular expressions:

```python
from ai_lib_python.guardrails import RegexFilter, GuardrailSeverity

# Match API key patterns
filter = RegexFilter(
    rule_id="api-keys",
    pattern=r"sk-[a-zA-Z0-9]{32}",
    severity=GuardrailSeverity.CRITICAL,
    replacement="[API KEY REDACTED]",
)
```

### LengthFilter

Enforce length constraints:

```python
from ai_lib_python.guardrails import LengthFilter, GuardrailSeverity

filter = LengthFilter(
    rule_id="length-limits",
    min_length=10,
    max_length=1000,
    severity=GuardrailSeverity.WARNING,
    count_mode="chars",  # or "words", "tokens_chars", "tokens_words"
)
```

### ProfanityFilter

Detect and filter inappropriate language:

```python
from ai_lib_python.guardrails import ProfanityFilter, GuardrailSeverity

filter = ProfanityFilter(
    rule_id="no-profanity",
    severity=GuardrailSeverity.WARNING,
    replacement="[CENSORED]",
)
```

### UrlFilter

Filter or detect URLs:

```python
from ai_lib_python.guardrails import UrlFilter, GuardrailSeverity

# Block all URLs
filter = UrlFilter(
    rule_id="block-urls",
    action="block",
    severity=GuardrailSeverity.INFO,
)

# Allow only specific domains
filter = UrlFilter(
    rule_id="allow-domains",
    action="allow",
    severity=GuardrailSeverity.INFO,
    allowed_domains=["example.com", "mydomain.com"],
)

# Block specific domains
filter = UrlFilter(
    rule_id="block-malicious",
    action="deny",
    severity=GuardrailSeverity.CRITICAL,
    blocked_domains=["malicious.com", "spam.com"],
)
```

### EmailFilter

Filter or detect email addresses:

```python
from ai_lib_python.guardrails import EmailFilter, GuardrailSeverity

# Block all emails
filter = EmailFilter(
    rule_id="no-emails",
    action="block",
    severity=GuardrailSeverity.INFO,
)

# Allow only specific domains
filter = EmailFilter(
    rule_id="internal-only",
    action="allow",
    severity=GuardrailSeverity.INFO,
    allowed_domains=["company.com"],
)
```

## Pre-configured Validators

For common use cases, use pre-configured validators:

### Input Validator

```python
from ai_lib_python.guardrails import ContentValidator

validator = ContentValidator.create_input_validator()
result = validator.check("User input here")
```

Includes:
- Length limits (1-10,000 chars)
- Profanity detection
- URL filtering (allow-only mode)
- Email filtering (allow-only mode)

### Output Validator

```python
validator = ContentValidator.create_output_validator()
result = validator.check("AI response here")
```

Includes:
- Length limits (1-50,000 chars)
- Profanity detection
- Malicious URL blocking
- PII detection (credit cards, SSN)

### PII Validator

```python
validator = ContentValidator.create_pii_validator()
filtered = validator.filter("Contact info included")
```

Detects:
- Email addresses
- Phone numbers
- Credit card numbers
- Social Security Numbers
- IP addresses

### Safety Validator

```python
from ai_lib_python.guardrails import SafetyValidator

validator = SafetyValidator(
    severity=GuardrailSeverity.CRITICAL,
    block_self_harm=True,
    block_harmful=True,
    block_profane=True,
)
```

Detects:
- Self-harm related content
- Harmful keywords
- Profanity

### Compliance Validator

```python
from ai_lib_python.guardrails import ComplianceValidator

# GDPR mode
validator = ComplianceValidator(
    gdpr_mode=True,
    hipaa_mode=False,
    severity=GuardrailSeverity.CRITICAL,
)

# HIPAA mode
validator = ComplianceValidator(
    gdpr_mode=False,
    hipaa_mode=True,
    severity=GuardrailSeverity.CRITICAL,
)
```

## Combining Guardrails

Use `CompositeGuardrail` to combine multiple rules:

```python
from ai_lib_python.guardrails import (
    CompositeGuardrail,
    KeywordFilter,
    RegexFilter,
    LengthFilter,
    GuardrailSeverity,
)

guardrail = CompositeGuardrail(
    rule_id="composite-check",
    guardrails=[
        KeywordFilter(
            rule_id="no-secrets",
            keywords=["sk-", "Bearer"],
            severity=GuardrailSeverity.CRITICAL,
        ),
        RegexFilter(
            rule_id="no-pii",
            pattern=r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",  # SSN pattern
            severity=GuardrailSeverity.CRITICAL,
        ),
        LengthFilter(
            rule_id="length",
            max_length=1000,
            severity=GuardrailSeverity.WARNING,
        ),
    ],
    severity=GuardrailSeverity.WARNING,
    stop_on_first=False,  # Check all rules
)

result = guardrail.check(content)
```

## Conditional Guardrails

Apply guardrails based on context:

```python
from ai_lib_python.guardrails import ConditionalGuardrail, KeywordFilter

guardrail = ConditionalGuardrail(
    rule_id="production-only",
    guardrail=KeywordFilter(
        rule_id="no-admin-commands",
        keywords=["admin", "delete-all"],
    ),
    condition=lambda ctx: ctx.get("environment") == "production",
)

guardrail.set_context({"environment": "production"})
result = guardrail.check("Execute admin command")
```

## Production Integration

### Before Sending to AI

```python
import asyncio
from ai_lib_python.guardrails import ContentValidator
from ai_lib_python.client import AiClient
from ai_lib_python.types.message import Message

async def chat_with_guardrails(user_input: str):
    # Validate input
    validator = ContentValidator.create_input_validator()
    result = validator.check(user_input)

    if not result.is_safe:
        print(f"Input blocked: {[v.message for v in result.violations]}")
        return None

    # Send to AI
    client = await AiClient.create("openai/gpt-4o", api_key="sk-...")
    response = await client.chat().messages([Message.user(user_input)]).execute()

    return response
```

### After Receiving from AI

```python
async def safe_chat(user_input: str):
    input_validator = ContentValidator.create_input_validator()
    output_validator = ContentValidator.create_output_validator()

    # Validate input
    input_result = input_validator.check(user_input)
    if not input_result.is_safe:
        print("Input blocked")
        return

    # Get AI response
    client = await AiClient.create("openai/gpt-4o", api_key="sk-...")
    response = await client.chat().messages([Message.user(user_input)]).execute()

    # Validate output
    output_result = output_validator.check(response.content)
    if not output_result.is_safe:
        print("Output contained PII or violations")
        # Option 1: Return filtered version
        return output_validator.filter(response.content)
        # Option 2: Return error
        # return "Content was filtered"

    return response.content
```

### Pipeline Integration

```python
from ai_lib_python.guardrails import ComplianceValidator

# Create GDPR-compliant pipeline
gdpr_validator = ComplianceValidator(
    gdpr_mode=True,
    severity=GuardrailSeverity.CRITICAL,
)

# Apply before user input
user_input = "User message with PII"
safe_input = gdpr_validator.filter(user_input)

# Apply before AI output
ai_response = "AI response with PII"
safe_response = gdpr_validator.filter(ai_response)
```

## Custom Guardrails

Create custom guardrails by extending the base class:

```python
from ai_lib_python.guardrails.base import Guardrail, GuardrailResult, GuardrailSeverity

class CustomGuardrail(Guardrail):
    def __init__(self, rule_id: str, config: dict):
        super().__init__(rule_id, GuardrailSeverity.WARNING)
        self.config = config

    def _check_impl(self, content: str) -> GuardrailResult:
        # Your custom logic here
        if self._should_block(content):
            return GuardrailResult.violated([
                self._create_violation("Custom violation reason")
            ], content)

        return GuardrailResult.safe(content=content)

    def _should_block(self, content: str) -> bool:
        # Your blocking logic
        return False
```

## Best Practices

1. **Separate Input and Output Validators**
   - Use different validators for user input vs AI output
   - Input validators can be more restrictive
   - Output validators focus on PII and harmful content

2. **Severity Levels Matter**
   - `CRITICAL`: Block immediately (API keys, passwords)
   - `ERROR`: Block but allow override option
   - `WARNING`: Log but allow
   - `INFO`: Log for analytics only

3. **Filtering is Better Than Blocking**
   - When possible, filter content instead of blocking
   - Improves user experience
   - Allows PII detection for compliance

4. **Test Your Guardrails**
   - Test edge cases
   - Verify false positive/negative rates
   - Monitor performance impact

5. **Combine Multiple Layers**
   - Use composite guardrails for comprehensive checking
   - Balance between security and usability

## API Reference

See the [API documentation](../api/guardrails.md) for complete details on all classes and methods.
