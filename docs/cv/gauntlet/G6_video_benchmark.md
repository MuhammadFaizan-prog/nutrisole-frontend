# G6.2 external real-video benchmark "web-mandi" (manifest only; NOT yet labelled, NOT evaluated)

**Status: manifest, uploader-grouped split and locked hashes are done; no clip has human labels, so no accuracy number exists on this benchmark yet.** Nothing here is Lahore footage: these are Wikimedia Commons uploads from other places and must never be reported as Lahore data.

Files: `ml/runs/G6/video_benchmark/manifest.csv` / `manifest.json` (per clip: Commons page URL, uploader, creator, licence + URL, region tag, upload date, classes guessed from title/description/categories, duration, fps, resolution, codec, sha256, split, annotation status), `locked_hashes.json` (sha256 per holdout/dev file), `candidates_no_download.csv` (YouTube, not used). Script `g6_video_manifest.py` (deterministic; re-run gives the same split). Video files stay outside git in `/workspace/work/cv/g6src/raw/` (~600 MB).

## Sources and rules
- Wikimedia Commons only, per-file licence read from the Commons API (`extmetadata`): CC BY-SA 4.0 (25), CC BY 3.0 (6), CC BY-SA 3.0 (3), CC0 (3), CC BY 4.0 (1). Attribution = uploader/creator + licence, as listed in the manifest. CC BY-SA clips: labels/derivatives we publish must be share-alike.
- **Rejected:** Pexels, Pixabay (ToS s.8 forbid ML use/scraping), Mixkit (no ML grant). YouTube: downloads fail with HTTP 403 in the sandbox; a "Creative Commons" label on YouTube is not taken as proof the uploader owns the footage; 3 search hits listed as UNVERIFIED in `candidates_no_download.csv`.
- Downloaded with a paced downloader (45 s gap, back-off on HTTP 429), 38/38 files, 52.7 min of video.

## Split (by uploader = recording-identity proxy; computed before any model saw the clips)
| split | clips | uploaders | minutes | notes |
|---|---|---|---|---|
| **holdout** (locked) | 15 | 14 | 44.3 | largest uploader share 13% (rule: <= 25%); 6 South-Asia-tagged clips |
| dev | 22 | 5 | 7.4 | Muktee1494 has 18 short single-produce clips (too dominant for the holdout) |
| train_only | 1 | 1 | - | Haikou wholesale market panorama: already used for G5 hard-negative mining, so it can never be a test clip |

Classes guessed from metadata (not verified): carrot 8, cucumber 6, capsicum 6, mango 3, tomato 2, banana/apple/citrus/lemon/guava 1 each, unknown 17 (market overviews). Several clips report odd frame rates (one 1000 fps = variable-frame-rate WebM); frames must be extracted by timestamp, not index.

## Gaps against the G6 target
- **38 independent files, not 60.** Counted at file level; long market walks are not split into "scenes" to inflate the count, and adjacent frames are never counted as independent.
- **No labels.** Each holdout clip needs per-segment produce class, boxes on sampled frames (e.g. 1 fps) and a quality/rotten flag by a person. Until then the benchmark can only give label-free stability proxies (tracks born per minute, label flips per track) and those were not run in G6 (CPU budget).
- Lighting, distance, hands, occlusion and camera motion are not annotated yet (`lighting=unannotated`).
- No Lahore footage; the Lahore phone field test (G6_device_validation_pending.md item 3) remains the real benchmark.

## Next (G7)
1. Label the 15 holdout clips (CVAT/Label Studio; 1 fps boxes + segment class/quality), double-review 10%.
2. Add Commons clips from more uploaders to reach >= 60 independent recordings; keep the 25% uploader cap.
3. Only then run G3 control vs candidates (IouTracker and ByteTrack) on the holdout once.
