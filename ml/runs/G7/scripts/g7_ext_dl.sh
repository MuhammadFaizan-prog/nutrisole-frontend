#!/bin/bash
# G7 staged downloads of ACCEPTED external sources (licence verified from the repository API before download). Idempotent.
cd /workspace/work/cv/g7data/ext; L=/workspace/work/cv/g7logs/ext_dl.log
dl(){ [ -f $1.DONE ] && return; curl -sL --retry 3 -m 3600 -A "NutriSoleResearch/0.3 (muhammadfaizanali18@gmail.com)" -o "$1" "$2" && echo "$(date -u +%T) $1 $(stat -c%s $1) sha256=$(sha256sum $1|cut -c1-64)" >> $L && touch $1.DONE; }
dl mangodhds_Anthracnose.zip https://data.mendeley.com/public-files/datasets/b4nrw5hyyc/files/361be86d-87a6-4c07-86e6-6d2594413935/file_downloaded
dl mangodhds_BacterialCanker.zip https://data.mendeley.com/public-files/datasets/b4nrw5hyyc/files/4666b488-fb6b-4527-a3bb-ff401e194c04/file_downloaded
dl mangodhds_Healthy.zip https://data.mendeley.com/public-files/datasets/b4nrw5hyyc/files/a68b287f-20a5-4e33-b5a2-9812d9e75c13/file_downloaded
dl mangodhds_Scab.zip https://data.mendeley.com/public-files/datasets/b4nrw5hyyc/files/3130a9e7-e4b1-45fd-9fb1-aa09eac1c8ca/file_downloaded
dl mangodhds_StemEndRot.zip https://data.mendeley.com/public-files/datasets/b4nrw5hyyc/files/e491e1fc-1fb1-4588-beb2-43c933617137/file_downloaded
dl mangodhds_Labels.csv https://data.mendeley.com/public-files/datasets/b4nrw5hyyc/files/5bbe3161-d85b-4196-95b2-1db845ff23f4/file_downloaded
dl zenodo17609211_dataset.zip https://zenodo.org/api/records/17609211/files/dataset.zip/content
dl w3fg8jjmzr_Guava_Dataset.zip "https://data.mendeley.com/public-files/datasets/w3fg8jjmzr/files/243a4600-798b-4b18-80c1-f26b069b7492/file_downloaded"
dl x4s2jz55dx_Dataset.rar "https://data.mendeley.com/public-files/datasets/x4s2jz55dx/files/10e9e9e3-267c-4be0-84e3-d530878f6e43/file_downloaded"
dl 56c75hvm7r_BANANA_DATASET.zip "https://data.mendeley.com/public-files/datasets/56c75hvm7r/files/e6fed512-91b4-413e-a7ea-7962ecf01a3c/file_downloaded"
touch ALL_DONE
