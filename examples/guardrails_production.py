"""
Production-ready example: Guardrails with content filtering.

This example demonstrates how to use guardrails to filter both user inputs
and AI model outputs for safety and compliance.

Key features:
- Input validation with guardrails
- Output filtering
- Custom guardrail rules
- Error handling
"""

import asyncio
import os

from ai_lib_python.client import AiClient
from ai_lib_python.guardrails import (
    ContentValidator,
    KeywordFilter,
    RegexFilter,
    ComplianceValidator,
    GuardrailSeverity,
)
from ai_lib_python.types.message import Message


# Configuration
API_KEY = os.getenv("OPENAI_API_KEY", "sk-your-api-key-here")
MODEL = "openai/gpt-4o"


async def main() -> None:
    """Main example demonstrating guardrails usage."""

    # ========================================
    # Example 1: Input validation
    # ========================================
    print("=== Example 1: Input Validation ===\n")

    # Create input validator
    input_validator = ContentValidator.create_input_validator(
        severity=GuardrailSeverity.WARNING,
    )

    # Add custom forbidden keywords (e.g., API keys, passwords)
    input_validator.add_guardrail(
        KeywordFilter(
            rule_id="no-api-keys",
            keywords=["sk-", "Bearer ", "password:"],
            severity=GuardrailSeverity.CRITICAL,
            case_sensitive=False,
        )
    )

    # Test inputs
    test_inputs = [
        "Hello, how are you?",
        "Here is my API key: sk-12345678",
        "My password is: secret123",
    ]

    for user_input in test_inputs:
        result = input_validator.check(user_input)
        if result.is_safe:
            print(f"✓ Safe: {user_input}")
        else:
            print(f"✗ Blocked: {user_input}")
            for violation in result.violations:
                print(f"  - {violation.message} (severity: {violation.severity.value})")
    print()

    # ========================================
    # Example 2: Output filtering
    # ========================================
    print("=== Example 2: Output Filtering ===\n")

    # Create output validator
    output_validator = ContentValidator.create_output_validator(
        severity=GuardrailSeverity.WARNING,
    )

    # Add PII detection
    output_validator.add_guardrail(
        RegexFilter(
            rule_id="no-phone-numbers",
            pattern=r"\b\d{3}[-\s.]?\d{3}[-\s.]?\d{4}\b",
            severity=GuardrailSeverity.INFO,
            replacement="[PHONE REDACTED]",
        )
    )

    # Simulated AI outputs
    test_outputs = [
        "The weather is nice today.",
        "Contact me at 555-123-4567 for details.",
        "Here is the information: 415-555-0100 and 212-555-9999",
    ]

    for output in test_outputs:
        result = output_validator.check(output)
        if result.is_safe:
            print(f"Safe output: {output}")
        else:
            print(f"Filtered output: {output}")
            for violation in result.violations:
                print(f"  - {violation.message}")

            # Apply filtering
            filtered = output_validator.filter(output)
            print(f"  After filtering: {filtered}")
    print()

    # ========================================
    # Example 3: Compliance validation (GDPR)
    # ========================================
    print("=== Example 3: GDPR Compliance ===\n")

    # Create GDPR compliance validator
    gdpr_validator = ComplianceValidator(
        gdpr_mode=True,
        hipaa_mode=False,
        severity=GuardrailSeverity.CRITICAL,
    )

    # Test content with PII
    pii_content = """
    User: John Smith
    Email: john.smith@example.com
    Phone: 555-123-4567
    Address: 123 Main St, Anytown, USA
    IP: 192.168.1.1
    """

    print(f"Original content:\n{pii_content}")

    result = gdpr_validator.check(pii_content)
    print(f"\nIs compliant: {result.is_safe}")

    if not result.is_safe:
        print(f"Violations found:")
        for violation in result.violations[:3]:  # Show first 3
            print(f"  - {violation.rule_id}: {violation.message}")

        # Apply filtering
        filtered = gdpr_validator.filter(pii_content)
        print(f"\nFiltered content:\n{filtered}")
    print()

    # ========================================
    # Example 4: End-to-end with guardrails
    # ========================================
    print("=== Example 4: End-to-End Chat with Guardrails ===\n")

    try:
        # Create client with resilience
        client = await (
            AiClient.builder()
            .model(MODEL)
            .api_key(API_KEY)
            .production_ready()
            .build()
        )

        # User input with potentially sensitive content
        user_message = "I need help with my account. My email is user@example.com"

        # Validate input
        input_result = input_validator.check(user_message)
        if not input_result.is_safe:
            print(f"Input blocked: {[v.message for v in input_result.violations]}")
            return

        # Send request
        print(f"User: {user_message}")

        # For this example, we'll just simulate without actual API call
        # In production:
        # response = await client.chat().messages([Message.user(user_message)]).execute()
        # print(f"AI: {response.content}")

        print("AI: I'd be happy to help with your account!")

        # Validate output (if needed)
        # output_result = output_validator.check(response.content)

    except Exception as e:
        print(f"Error: {e}")
        print("\nNote: To run this example with real API calls, set OPENAI_API_KEY")


if __name__ == "__main__":
    asyncio.run(main())
