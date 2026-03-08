"""
既存ラベルのクリーンアップ。

debidebi_frame_*.txt → class_id=0 (debidebi) のみ残す
runrun_frame_*.txt   → class_id=1 (runrun)   のみ残す

ファイル名でキャラクターが確定しているため、
相手のクラスが混入していても除去できる。
"""
from pathlib import Path

DATASET_ROOT = Path(__file__).parent.parent / "vtuber_dataset"
CHAR_CLASS = {"debidebi": 0, "runrun": 1}


def fix_split(split: str) -> None:
    label_dir = DATASET_ROOT / split / "labels"
    if not label_dir.exists():
        return

    total, removed = 0, 0
    for label_path in sorted(label_dir.glob("*.txt")):
        # ファイル名からキャラクターを判別
        char = next((c for c in CHAR_CLASS if label_path.stem.startswith(c)), None)
        if char is None:
            continue

        keep_class = CHAR_CLASS[char]
        lines = label_path.read_text().strip().splitlines()
        kept = [l for l in lines if l.strip() and int(l.split()[0]) == keep_class]

        if len(kept) != len(lines):
            removed += len(lines) - len(kept)
            label_path.write_text("\n".join(kept) + "\n" if kept else "")
            print(f"  {label_path.name}: {len(lines)} → {len(kept)} boxes")

        total += 1

    print(f"[{split}] {total} files processed, {removed} wrong-class boxes removed")


for split in ("train", "valid"):
    fix_split(split)

print("\nDone. Re-run training to apply cleaned labels.")
