# Champion: CodeT5p-220M (frozen)

- Selection policy: median combined F1 across seeds (tie-breakers: L2 to mean per-tech F1 → per-tech spread)
- Chosen run: codet5p_220m_champion_lr4e-5_bs8_ep6_wd0.01_acc1_seed42_20250925_191300_job16122826
- Chosen seed: 42
- Combined F1: 0.778626
- Per-tech F1 → chef: 0.6976744186046512, ansible: 0.8837209302325582, puppet: 0.7555555555555555
- Source checkpoint dir: /Users/colemei/Library/Mobile Documents/com~apple~CloudDocs/01.Work/04.Master/Course/Research Program/Project/02.LLM-IaC-SecEval-Models/models/experiments/encoder/codet5p_220m_champion_lr4e-5_bs8_ep6_wd0.01_acc1_seed42_20250925_191300_job16122826
- Frozen thresholds: artifacts/models/champion/frozen_thresholds.yaml
- Hosted on Hugging Face: https://huggingface.co/colemei/codet5p-220m-iac-security
