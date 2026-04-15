"""
deploy_custom_skill.py — Deploy the custom skill Azure Function and write the URL to .env.

Usage:
    python deploy_custom_skill.py

Prerequisites:
    - Azure Functions Core Tools (func) installed
    - Azure CLI logged in
    - CUSTOM_SKILL_FUNCTION_APP and CUSTOM_SKILL_RESOURCE_GROUP set in .env
"""

import json
import os
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv()

FUNCTION_APP = os.environ.get("CUSTOM_SKILL_FUNCTION_APP", "smoke-func")
RESOURCE_GROUP = os.environ.get("CUSTOM_SKILL_RESOURCE_GROUP", "SSS3PT_mcarter_azs")
SKILL_DIR = os.path.join(os.path.dirname(__file__), "custom_skill")


def run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  STDERR: {result.stderr[:500]}")
    return result


def main():
    # 1. Deploy the function
    print(f"Deploying custom skill to {FUNCTION_APP}...")
    result = run(
        ["func", "azure", "functionapp", "publish", FUNCTION_APP, "--python"],
        cwd=SKILL_DIR,
    )
    if result.returncode != 0:
        print(f"ERROR: Deployment failed.\n{result.stderr[:1000]}")
        sys.exit(1)
    print("  Deployment succeeded.")

    # 2. Get the function URL with code (function key)
    print("Fetching function URL...")
    result = run([
        "az", "functionapp", "function", "show",
        "--name", FUNCTION_APP,
        "--resource-group", RESOURCE_GROUP,
        "--function-name", "analyze",
        "--query", "invokeUrlTemplate",
        "-o", "tsv",
    ])
    base_url = result.stdout.strip()

    # Get the function key
    key_result = run([
        "az", "functionapp", "function", "keys", "list",
        "--name", FUNCTION_APP,
        "--resource-group", RESOURCE_GROUP,
        "--function-name", "analyze",
        "--query", "default",
        "-o", "tsv",
    ])
    func_key = key_result.stdout.strip()

    if base_url and func_key:
        full_url = f"{base_url}?code={func_key}"
    elif base_url:
        full_url = base_url
    else:
        # Fallback: construct from known pattern
        full_url = f"https://{FUNCTION_APP}.azurewebsites.net/api/analyze"
        print(f"  WARNING: Could not fetch URL dynamically, using fallback: {full_url}")

    print(f"\nCustom Skill URL: {full_url}")

    # 3. Update .env
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            content = f.read()
        if "CUSTOM_SKILL_URL=" in content:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("CUSTOM_SKILL_URL="):
                    lines[i] = f"CUSTOM_SKILL_URL={full_url}"
                    break
            with open(env_path, "w") as f:
                f.write("\n".join(lines))
            print(f"  Updated CUSTOM_SKILL_URL in .env")
        else:
            with open(env_path, "a") as f:
                f.write(f"\nCUSTOM_SKILL_URL={full_url}\n")
            print(f"  Appended CUSTOM_SKILL_URL to .env")
    else:
        print(f"  WARNING: .env not found at {env_path}")

    print("\nDone. You can now run the skillset tests.")


if __name__ == "__main__":
    main()
