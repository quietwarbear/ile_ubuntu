"""One-off: copy existing uploaded lesson videos to Cloudflare Stream (I4 phase 2).

    python migrate_videos_to_stream.py            # dry run: prints what it would move
    python migrate_videos_to_stream.py --apply    # does it
    python migrate_videos_to_stream.py --apply --limit 5

Dry run is the default and touches nothing (no Cloudflare calls, no database
writes). Run it from backend/ with the production env vars loaded.

For each video file record that isn't on Stream yet:
  - in object storage (s3_key): Stream copies it from a presigned link
    (valid 6 hours). The record gains stream_uid and storage "stream"; the
    original object is kept and its key moved to legacy_s3_key, so nothing is
    deleted. Lessons keep pointing at the same file id, so no lesson changes.
  - on local disk only: skipped. Railway disk is wiped on redeploy, so these
    bytes are almost always gone already (see /api/files/integrity/report).

Stream processes copies in the background. The app checks a video's state
when someone opens it, so they start playing once ready. Automatic captions
are requested at that same moment.
"""

import argparse
import sys

from database import files_col
import storage
import stream

COPY_LINK_TTL = 6 * 3600


def candidates():
    return list(files_col.find(
        {"file_category": "video", "stream_uid": {"$exists": False}},
        {"_id": 0},
    ).sort("uploaded_at", 1))


def plan(records):
    moves, skips = [], []
    for r in records:
        if r.get("s3_key"):
            moves.append(r)
        else:
            skips.append((r, "only on local disk, not in object storage"))
    return moves, skips


def migrate(record):
    name = record.get("original_filename") or record.get("filename") or record["id"]
    url = storage.presigned_get(record["s3_key"], name, record.get("mime_type") or "video/mp4",
                                inline=True, ttl=COPY_LINK_TTL)
    uid = stream.copy_from_url(url, name)
    files_col.update_one({"id": record["id"]}, {
        "$set": {"stream_uid": uid, "storage": "stream", "stream_state": "queued",
                 "stream_ready": False, "legacy_s3_key": record["s3_key"]},
        "$unset": {"s3_key": ""},
    })
    return uid


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="actually copy (default: dry run)")
    parser.add_argument("--limit", type=int, default=0, help="move at most this many")
    args = parser.parse_args(argv)

    moves, skips = plan(candidates())
    if args.limit:
        moves = moves[:args.limit]
    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"[{mode}] {len(moves)} video(s) to copy to Stream, {len(skips)} skipped")
    for r in moves:
        size = (r.get("file_size") or 0) / 1_000_000
        print(f"  move  {r['id']}  {size:8.1f} MB  {r.get('original_filename')}  lesson={r.get('lesson_id')}")
    for r, why in skips:
        print(f"  skip  {r['id']}  {r.get('original_filename')}  ({why})")

    if not args.apply:
        print("Nothing changed. Re-run with --apply to copy.")
        return 0
    if not stream.enabled() or not storage.s3_enabled():
        print("Stream and object storage must both be configured to apply.", file=sys.stderr)
        return 2

    failed = 0
    for r in moves:
        try:
            uid = migrate(r)
            print(f"  copied {r['id']} -> {uid}")
        except Exception as exc:          # keep going; report at the end
            failed += 1
            print(f"  FAILED {r['id']}: {exc}", file=sys.stderr)
    print(f"Done: {len(moves) - failed} copied, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
