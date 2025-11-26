先安装torch
pip install torch==2.9.0 torchvision torchaudio torchcodec --index-url https://download.pytorch.org/whl/cu121 -i https://pypi.tuna.tsinghua.edu.cn/simple

然后搞到 umap 解压到环境的site-packages
# 进入目标 site-packages 目录
cd /root/data/_miniconda3/envs/mintai/lib/python3.10/site-packages
# 解压压缩包
tar -xzvf /root/data/MintaiDialect/umap_backup.tar.gz

# asr
funasr==0.8.8
modelscope==1.10.0
transformers==4.49.0

numpy==1.23.5
python-multipart
rotary_embedding_torch
uvicorn
fastapi
addict

# 后端
sqlalchemy
pydantic_settings
openai
pydub
# sudo apt install ffmpeg -y

# llm
vllm

Successfully installed anthropic-0.71.0 apache-tvm-ffi-0.1.3 astor-0.8.1 blake3-1.0.8 cachetools-6.2.2 cbor2-5.7.1 click-8.2.1 cloudpickle-3.1.2 compressed-tensors-0.12.2 cuda-bindings-13.0.3 cuda-pathfinder-1.3.2 cuda-python-13.0.3 cupy-cuda12x-13.6.0 depyf-0.20.0 diskcache-5.6.3 dnspython-2.8.0 docstring-parser-0.17.0 email-validator-2.3.0 fastapi-cli-0.0.16 fastapi-cloud-cli-0.5.1 fastar-0.7.0 fastrlock-0.8.3 flashinfer-python-0.5.2 gguf-0.17.1 httptools-0.7.1 interegular-0.3.3 jsonschema-4.25.1 jsonschema-specifications-2025.9.1 lark-1.2.2 llguidance-1.3.0 llvmlite-0.44.0 lm-format-enforcer-0.11.3 loguru-0.7.3 markdown-it-py-4.0.0 mdurl-0.1.2 mistral_common-1.8.5 model-hosting-container-standards-0.1.9 msgspec-0.20.0 ninja-1.13.0 numba-0.61.2 numpy-2.2.6 nvidia-cudnn-frontend-1.16.0 nvidia-cutlass-dsl-4.3.0 nvidia-ml-py-13.580.82 openai-harmony-0.0.8 opencv-python-headless-4.12.0.88 outlines_core-0.2.11 partial-json-parser-0.2.1.1.post7 prometheus-fastapi-instrumentator-7.1.0 prometheus_client-0.23.1 psutil-7.1.3 py-cpuinfo-9.0.0 pybase64-1.4.2 pycountry-24.6.1 pydantic-extra-types-2.10.6 pygments-2.19.2 python-json-logger-4.0.0 pyzmq-27.1.0 ray-2.52.0 referencing-0.37.0 rich-14.2.0 rich-toolkit-0.16.0 rignore-0.7.6 rpds-py-0.29.0 sentry-sdk-2.46.0 setproctitle-1.3.7 supervisor-4.3.0 tabulate-0.9.0 tiktoken-0.12.0 tokenizers-0.22.1 transformers-4.57.2 typer-0.20.0 uvloop-0.22.1 vllm-0.11.2 watchfiles-1.1.1 websockets-15.0.1 xformers-0.0.33.post1 xgrammar-0.1.25
