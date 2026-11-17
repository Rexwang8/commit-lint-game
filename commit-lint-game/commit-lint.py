import argparse
import json
import re
import sys


FLAGS = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
    "ASCII": re.ASCII
}


def load_rules(path):
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    rules = []

    for rule in config["rules"]:
        flags = 0

        for flag in rule.get("flags", []):
            if flag not in FLAGS:
                raise ValueError(f"Unknown regex flag: {flag}")
            flags |= FLAGS[flag]

        rules.append((
            rule["name"],
            re.compile(rule["pattern"], flags),
            rule["message"]
        ))

    return rules


def validate(message, rules):
    errors = []

    for name, pattern, error_message in rules:
        if not pattern.search(message):
            errors.append((name, error_message))

    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validate a commit message against configured rules."
    )

    parser.add_argument(
        "-m", "--message",
        help="Commit message to validate"
    )

    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read commit message from stdin"
    )

    parser.add_argument(
        "-c", "--config",
        default="commit-lint-game/commit-rules.json",
        help="Path to rules configuration"
    )

    args = parser.parse_args()

    if args.message is not None:
        message = args.message
    elif args.stdin:
        message = sys.stdin.read()
    else:
        parser.error("Provide --message or --stdin")

    try:
        rules = load_rules(args.config)
        errors = validate(message, rules)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2

    if errors:
        print("Commit message validation failed:\n")

        for name, message in errors:
            print(f"  [{name}] {message}")

        return 1

    print("Commit message passed validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())