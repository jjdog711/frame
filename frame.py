
from pathlib import Path
import json
import argparse
import uuid
from datetime import datetime
import zipfile
import os

# Define paths
base_dir = Path("./frame")
output_zip_path = "frame_v8_updated.zip"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_full_path(relative_path):
    return base_dir / relative_path

def detect_file_type(data):
    if isinstance(data, dict):
        return "dict"
    elif isinstance(data, list):
        return "list"
    else:
        return "unknown"

def append_entry(path, content):
    data = load_json(path)

    new_entry = {
        "id": f"cli_{datetime.utcnow().strftime('%Y-%m-%d')}_{uuid.uuid4().hex[:6]}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "title": "CLI Appended Entry",
        "content": content,
        "emotions": {},
        "tags": ["cli", "manual"]
    }

    if isinstance(data, dict) and "entries" in data and isinstance(data["entries"], list):
        data["entries"].append(new_entry)
    elif isinstance(data, dict) and "procedures" in data and isinstance(data["procedures"], list):
        data["procedures"].append(new_entry)
    elif isinstance(data, list):
        data.append(new_entry)
    else:
        raise ValueError("Cannot append to this structure")

    save_json(path, data)
    return f"Appended to {path.name}"

def update_entry(path, key, value):
    data = load_json(path)
    data[key] = value
    save_json(path, data)
    return f"Updated {key} in {path.name}"

def zip_frame(output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for foldername, _, filenames in os.walk(base_dir):
            for filename in filenames:
                filepath = os.path.join(foldername, filename)
                arcname = os.path.relpath(filepath, base_dir.parent)
                zipf.write(filepath, arcname=arcname)
    return output_path

def run_batch(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        batch_data = json.load(f)

    results = []

    for update in batch_data:
        target_path = get_full_path(update["file"])
        data = load_json(target_path)
        mode = detect_file_type(data)

        if update.get("mode") == "append" or (mode == "list" or ("entries" in data and isinstance(data["entries"], list))):
            text = update.get("text")
            if text is None:
                result = f"Skipped: {update['file']} (missing text for append)"
            else:
                result = append_entry(target_path, text)
        elif update.get("mode") == "update" or (mode == "dict" and update.get("key") and update.get("value") is not None):
            key = update.get("key")
            value = update.get("value")
            if key is None or value is None:
                result = f"Skipped: {update['file']} (missing key/value for update)"
            else:
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except Exception:
                        pass
                result = update_entry(target_path, key, value)
        else:
            result = f"Skipped: {update['file']} (unrecognized structure or insufficient data)"
        results.append(result)

    return results

def main():
    parser = argparse.ArgumentParser(description="FRAME CLI with Smart and Batch Update")
    subparsers = parser.add_subparsers(dest="command")

    append_parser = subparsers.add_parser("append")
    append_parser.add_argument("file", help="Relative path to FRAME file")
    append_parser.add_argument("content", help="Text content to append")

    update_parser = subparsers.add_parser("update")
    update_parser.add_argument("file", help="Relative path to FRAME file")
    update_parser.add_argument("key", help="Key to update or insert")
    update_parser.add_argument("value", help="Value to assign (as JSON string)")

    smart_parser = subparsers.add_parser("smart-update")
    smart_parser.add_argument("file", help="Relative path to FRAME file")
    smart_parser.add_argument("--key", help="Key (for dict-style update)")
    smart_parser.add_argument("--value", help="Value (as string or JSON)")
    smart_parser.add_argument("--text", help="Text content for append")

    batch_parser = subparsers.add_parser("batch-update")
    batch_parser.add_argument("batch_file", help="Path to JSON file describing batch updates")

    subparsers.add_parser("zip")

    args = parser.parse_args()

    if args.command == "append":
        result = append_entry(get_full_path(args.file), args.content)
        print(result)

    elif args.command == "update":
        parsed_value = json.loads(args.value)
        result = update_entry(get_full_path(args.file), args.key, parsed_value)
        print(result)

    elif args.command == "smart-update":
        path = get_full_path(args.file)
        data = load_json(path)
        mode = detect_file_type(data)

        if mode == "dict" and args.key and args.value:
            parsed_value = json.loads(args.value)
            result = update_entry(path, args.key, parsed_value)
        elif mode in ["list", "dict"] and args.text:
            result = append_entry(path, args.text)
        else:
            raise ValueError("Insufficient parameters for smart update.")
        print(result)

    elif args.command == "batch-update":
        results = run_batch(args.batch_file)
        for res in results:
            print(res)

    elif args.command == "zip":
        result = zip_frame(output_zip_path)
        print(f"FRAME zipped to: {result}")

if __name__ == "__main__":
    main()
