
import argparse
import json
import re
import sys
from pathlib import Path


FLAGS = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
    "ASCII": re.ASCII
}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_rules(path):
    config_path = Path(path).resolve()
    config = load_json(config_path)

    rules = []

    for rule in config["rules"]:
        rule = rule.copy()
        rule_type = rule.get("type", "regex")

        flags = 0
        for flag in rule.get("flags", []):
            if flag not in FLAGS:
                raise ValueError(f"Unknown regex flag: {flag}")
            flags |= FLAGS[flag]

        if rule_type == "regex":
            rule["_compiled"] = re.compile(rule["pattern"], flags)

        elif rule_type == "word_list":
            word_file = config_path.parent / rule["file"]
            words = load_json(word_file)

            rule["_words"] = [
                re.compile(r"\b" + re.escape(word) + r"\b", flags)
                for word in words
            ]

        elif rule_type not in (
                "alphanumeric_even",
                "palindrome",
                "digit_sum"
            ):
            raise ValueError(f"Unknown rule type: {rule_type}")

        rules.append(rule)

    return rules


def validate_rule(message, rule):
    rule_type = rule.get("type", "regex")

    if rule_type == "regex":
        return bool(rule["_compiled"].search(message))

    if rule_type == "alphanumeric_even":
        count = sum(c.isalnum() for c in message)
        return count % 2 == 0

    if rule_type == "word_list":
        matches = sum(
            bool(pattern.search(message))
            for pattern in rule["_words"]
        )

        return matches >= rule.get("min_matches", 1)

    if rule_type == "palindrome":
        min_length = rule.get("min_length", 5)

        words = re.findall(r"[a-zA-Z]+", message)

        return any(
            len(word) >= min_length and word.lower() == word.lower()[::-1]
            for word in words
        )

    if rule_type == "digit_sum":
        total = sum(int(digit) for digit in re.findall(r"\d", message))
        return total == rule.get("target", 25)

    return False


def validate(message, rules):
    for rule in rules:
        if not validate_rule(message, rule):
            return [(rule["name"], rule["message"])]
            

    return []



def main():
    parser = argparse.ArgumentParser(
        description="Validate a commit message against configured rules."
    )

    parser.add_argument("-m", "--message")
    parser.add_argument("--stdin", action="store_true")
    SCRIPT_DIR = Path(__file__).resolve().parent

    parser.add_argument(
    "-c", "--config",
    default=str(SCRIPT_DIR / "commit-rules.json")
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

    except (OSError, ValueError, KeyError, json.JSONDecodeError, re.error) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2

    if errors:
        print("Commit message validation failed:\n")

        for name, error_message in errors:
            print(f"  [{name}] {error_message}")

        return 1

    print("Commit message passed validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
