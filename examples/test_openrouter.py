"""Test OpenRouter connection directly."""

import openai
import httpx
from src.config import settings


def test_openrouter():
    """Test basic OpenRouter connection."""
    print("Testing OpenRouter connection...")
    print(f"Base URL: {settings.openrouter_base_url}")
    print(f"Model: {settings.openrouter_model}")
    print(
        f"API Key: {settings.openrouter_api_key[:20]}...{settings.openrouter_api_key[-5:]}"
    )

    # Create HTTP client with SSL verification disabled (for corporate networks)
    http_client = httpx.Client(verify=False)

    client = openai.OpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        default_headers={
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Smart-Meet Lite",
        },
        http_client=http_client,
    )

    try:
        # Simple test without structured output first
        response = client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {
                    "role": "user",
                    "content": "Say 'Hello from OpenRouter' in JSON format with a 'message' field.",
                }
            ],
            temperature=0,
            max_tokens=100,
        )

        print("\n✓ Basic connection successful!")
        print(f"Response: {response.choices[0].message.content}")

        # Now test with structured output
        print("\nTesting structured output...")
        response2 = client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {
                    "role": "user",
                    "content": "Return a JSON object with 'status' and 'message' fields.",
                }
            ],
            temperature=0,
            max_tokens=100,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "test_response",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string"},
                            "message": {"type": "string"},
                        },
                        "required": ["status", "message"],
                        "additionalProperties": False,
                    },
                },
            },
        )

        print("✓ Structured output successful!")
        print(f"Response: {response2.choices[0].message.content}")

    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        print(f"Error type: {type(e).__name__}")

        # Print more detailed error info
        import traceback

        print("\nDetailed error:")
        traceback.print_exc()

        # Check if it's an API error
        if hasattr(e, "response"):
            print(
                f"Status code: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}"
            )
            print(
                f"Response body: {e.response.text if hasattr(e.response, 'text') else 'N/A'}"
            )

        # Check for common issues
        if "Connection" in str(e):
            print("\n⚠️  Connection issue detected. Possible causes:")
            print("   - Network/firewall blocking OpenRouter API")
            print("   - Corporate proxy settings required")
            print("   - Invalid API endpoint URL")


if __name__ == "__main__":
    test_openrouter()
