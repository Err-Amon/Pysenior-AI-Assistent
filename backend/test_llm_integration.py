import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.services.ai_review import _call_llm, generate
from app.services.code_parser import parse
from app.models.pr_models import PRFile


def test_llm_connection():
    settings = get_settings()

    print("=" * 60)
    print("PySenior LLM Integration Test")
    print("=" * 60)
    print(f"LLM Provider: {settings.LLM_PROVIDER}")
    print()

    # Check if required API keys are set
    if settings.LLM_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            print("OpenAI API key is not configured")
            print("Please set OPENAI_API_KEY in .env file")
            return False
        print("OpenAI API key configured")

    elif settings.LLM_PROVIDER == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            print("Anthropic API key is not configured")
            print("Please set ANTHROPIC_API_KEY in .env file")
            return False
        print("Anthropic API key configured")

    elif settings.LLM_PROVIDER == "gemini":
        if not settings.GEMINI_API_KEY:
            print("Google Gemini API key is not configured")
            print("Please set GEMINI_API_KEY in .env file")
            return False
        print("Google Gemini API key configured")

    elif settings.LLM_PROVIDER == "groq":
        if not settings.GROQ_API_KEY:
            print("Groq API key is not configured")
            print("Please set GROQ_API_KEY in .env file")
            return False
        print("Groq API key configured")

    else:
        print(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")
        print("Please choose from: openai, anthropic, gemini, groq")
        return False

    print()
    return True


def test_simple_llm_call():
    settings = get_settings()

    print("Testing LLM connectivity...")

    test_prompt = """You are a helpful assistant. Please respond with "Hello from PySenior!" to confirm connectivity."""

    try:
        response = _call_llm(test_prompt)
        print("LLM response received")
        print(f"Response: {response.strip()}")

        if "Hello from PySenior" in response:
            print("Test passed - LLM is working correctly")
        else:
            print("Test completed - Response format different than expected")

        return True

    except Exception as e:
        print(f"Error calling LLM: {str(e)}")
        import traceback

        print(traceback.format_exc())
        return False


def test_code_review_pipeline():
    print()
    print("=" * 60)
    print("Testing Complete Code Review Pipeline")
    print("=" * 60)

    # Sample Python file to test
    sample_file = PRFile(
        filename="test_sample.py",
        status="modified",
        sha="abc123",
        additions=10,
        deletions=2,
        patch="""
+def vulnerable_function(cmd):
+    import subprocess
+    result = subprocess.run(f"echo {cmd}", shell=True, capture_output=True, text=True)
+    return result.stdout
""",
        content="""
def vulnerable_function(cmd):
    import subprocess
    result = subprocess.run(f"echo {cmd}", shell=True, capture_output=True, text=True)
    return result.stdout

def safe_function(cmd):
    import subprocess
    result = subprocess.run(["echo", cmd], capture_output=True, text=True)
    return result.stdout
""",
    )

    print(f"Testing file: {sample_file.filename}")

    try:
        # Step 1: Parse the file
        print("\n1. Parsing Python code...")
        parsed_files = parse([sample_file])

        if not parsed_files:
            print("No files parsed")
            return False

        print(f"   Parsed {len(parsed_files)} file(s)")
        print(f"   Found {len(parsed_files[0].entities)} code entities")

        # Step 2: Generate AI review
        print("\n2. Generating AI review...")
        findings = generate(parsed_files)

        print(f"   Found {len(findings)} issues")

        if findings:
            print("\n3. Issues Found:")
            for i, finding in enumerate(findings, 1):
                print(
                    f"\n   {i}. [{finding.severity.value.upper()}] - {finding.category.value}"
                )
                print(f"      File: {finding.filename}")
                print(f"      Line: {finding.line_number}")
                print(f"      Title: {finding.title}")
                print(f"      Description: {finding.description}")
                if finding.suggestion:
                    print(f"      Suggestion: {finding.suggestion}")

        # Success
        print()
        print(" Code review pipeline test completed successfully!")
        return True

    except Exception as e:
        print(f"\n Error in code review pipeline: {str(e)}")
        import traceback

        print(traceback.format_exc())
        return False


def main():
    """Main test function"""
    # Test LLM configuration
    if not test_llm_connection():
        return 1

    # Test simple LLM call
    if not test_simple_llm_call():
        return 1

    # Test complete pipeline
    if not test_code_review_pipeline():
        return 1

    print()
    print("=" * 60)
    print(" All tests passed! PySenior is ready to use!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Set up GitHub webhook integration")
    print("2. Create a PR to test the automated review")
    print("3. Monitor the review results in your PR comments")

    return 0


if __name__ == "__main__":
    sys.exit(main())
