# AISHELL-1 ASR 自动评测

用途：使用公开中文普通话 AISHELL-1 test 集测试本项目 ASR 服务，输出 CER、WER、SER、成功率和平均耗时。

AISHELL-1 官方地址：https://www.openslr.org/33/

## 1. 下载与整理

AISHELL-1 压缩包约 15GB，建议放到空间充足的位置，例如：

```powershell
cd C:\Users\FYF\Documents\GitHub\FuChuangSai_A22

python scripts\evaluation\aishell_asr_eval.py prepare `
  --root "F:\AISHELL-1" `
  --download `
  --extract `
  --manifest "F:\AISHELL-1\aishell_test_manifest.jsonl" `
  --report "F:\AISHELL-1\aishell_prepare_report.json"
```

如果你已经手动下载了 `data_aishell.tgz`：

```powershell
python scripts\evaluation\aishell_asr_eval.py prepare `
  --root "F:\AISHELL-1" `
  --archive "F:\AISHELL-1\data_aishell.tgz" `
  --extract `
  --manifest "F:\AISHELL-1\aishell_test_manifest.jsonl" `
  --report "F:\AISHELL-1\aishell_prepare_report.json"
```

如果已经解压完成，只想重新生成清单：

```powershell
python scripts\evaluation\aishell_asr_eval.py prepare `
  --root "F:\AISHELL-1" `
  --manifest "F:\AISHELL-1\aishell_test_manifest.jsonl" `
  --report "F:\AISHELL-1\aishell_prepare_report.json"
```

## 2. 小样本测试

先确认 SSH 隧道和 speech-service 已启动，本地 `29100` 能访问：

```powershell
curl.exe http://127.0.0.1:29100/health
```

跑 20 条小样本：

```powershell
python scripts\evaluation\aishell_asr_eval.py eval `
  --manifest "F:\AISHELL-1\aishell_test_manifest.jsonl" `
  --url "http://127.0.0.1:29100/transcribe" `
  --mode a22_json `
  --limit 20 `
  --timeout 300 `
  --out-jsonl "F:\AISHELL-1\aishell_asr_20.jsonl" `
  --summary "F:\AISHELL-1\aishell_asr_20_summary.json"
```

## 3. 全量测试

确认 20 条没有 HTTP 500 或超时后，再跑全量：

```powershell
python scripts\evaluation\aishell_asr_eval.py eval `
  --manifest "F:\AISHELL-1\aishell_test_manifest.jsonl" `
  --url "http://127.0.0.1:29100/transcribe" `
  --mode a22_json `
  --timeout 300 `
  --out-jsonl "F:\AISHELL-1\aishell_asr_full.jsonl" `
  --summary "F:\AISHELL-1\aishell_asr_full_summary.json"
```

## 4. 指标说明

- `CER`：字符错误率，更适合中文 ASR。
- `WER`：词错误率。脚本优先使用 `jieba` 分词；如果未安装，则退化为中文逐字 token。
- `SER`：句错误率，只要一句识别结果和标准文本不完全一致，就记为错误句。
- `success_rate`：接口成功率。
- `avg_latency_sec`：成功样本平均识别耗时。

报告中建议同时写 CER、WER、SER，因为赛题写 WER/SER，但中文 ASR 通常更看 CER。
