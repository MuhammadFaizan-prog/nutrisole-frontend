#!/bin/bash
# G6.4 label-free stability on web-mandi DEV clips (never the holdout), G3 control det, IouTracker vs ByteTrack(DEV pick). Runs after TRACK_R1_DONE, under the CPU lock.
cd /workspace/work/nutrisole; source /workspace/work/cvenv/bin/activate; L=/workspace/work/cv/g6logs
until [ -f $L/TRACK_R1_DONE ]; do sleep 60; done
[ -f $L/LFS_DONE ] && exit 0
P=$(python -c "import json;print(json.dumps(json.load(open('$L/bt_pick.json'))['params']))")
CL=$(python -c "import json;d=json.load(open('ml/runs/G6/video_benchmark/manifest.json'));print(' '.join(c['file'] for c in d['clips'] if c['split']=='dev' and c['downloaded']))")
exec 9>$L/cpu.lock; flock 9
python ml/eval/label_free_stability.py --det /workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx --clips $CL --out ml/runs/G6/tracking/label_free_webdev.json --bt "$P" --stride 2 --max-s 40 > $L/lfs.log 2>&1 && touch $L/LFS_DONE
