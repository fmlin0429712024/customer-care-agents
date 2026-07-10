# Copy-Paste Commands for GCP Setup

直接复制下面的命令到你的终端执行。

---

## 1️⃣ 安装 Google Cloud CLI

```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud --version
```

---

## 2️⃣ 登录 GCP 并设置项目

```bash
gcloud auth login
gcloud config set project linkhealth-care-2024
gcloud config list
```

**会弹出浏览器让你登录** ← **你需要在这里批准！**

---

## 3️⃣ 启用 Gemini API

```bash
gcloud services enable generativeaiapi.googleapis.com
gcloud services list --enabled | grep generative
```

---

## 4️⃣ 创建服务账号

```bash
gcloud iam service-accounts create refund-agent-dev \
  --display-name="Refund Agent — Local Development"
  
gcloud iam service-accounts list
```

---

## 5️⃣ 授权权限

```bash
gcloud projects add-iam-policy-binding linkhealth-care-2024 \
  --member=serviceAccount:refund-agent-dev@linkhealth-care-2024.iam.gserviceaccount.com \
  --role=roles/aiplatform.user \
  --quiet
```

---

## 6️⃣ 下载密钥文件

```bash
gcloud iam service-accounts keys create ~/gcp-refund-agent-key.json \
  --iam-account=refund-agent-dev@linkhealth-care-2024.iam.gserviceaccount.com

chmod 600 ~/gcp-refund-agent-key.json
ls -la ~/gcp-refund-agent-key.json
```

✅ **密钥文件现在在你的电脑上** — 绝对不要分享或提交到 GitHub！

---

## 7️⃣ 创建 .env 文件

```bash
cd /Users/fmlin/Documents/customer-refund-agent/adk_refund

cp .env.example .env

nano .env
```

在编辑器中，更新这三行（粘贴你的值）：

```
GOOGLE_CLOUD_PROJECT=linkhealth-care-2024
GOOGLE_APPLICATION_CREDENTIALS=/Users/fmlin/gcp-refund-agent-key.json
GENAI_API_KEY=<你的-Gemini-API-Key>
```

**获取 Gemini API Key：**
1. 打开 https://console.cloud.google.com/apis/credentials
2. 点击 "Create Credentials" → "API Key"
3. 复制 API Key
4. 粘贴到 .env 中的 GENAI_API_KEY

按 `Ctrl+X` 然后 `Y` 保存退出。

---

## 8️⃣ 验证认证

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/Users/fmlin/gcp-refund-agent-key.json

python3 -c "
from google.auth import default
creds, project = default()
print(f'✓ Project: {project}')
print(f'✓ Service Account: {creds.service_account_email}')
"
```

应该输出类似：
```
✓ Project: linkhealth-care-2024
✓ Service Account: refund-agent-dev@linkhealth-care-2024.iam.gserviceaccount.com
```

---

## 9️⃣ 测试 Gemini 连接

```bash
cd /Users/fmlin/Documents/customer-refund-agent/adk_refund

source venv/bin/activate

python test_gemini.py
```

应该输出：
```
✓ google-genai imported
✓ google-adk imported
✓ Gemini client created
✓ gemini-2.5-pro is available
✓ ADK Agent created
✓ ALL TESTS PASSED
```

---

## 🔟 运行第一个场景

```bash
python run_refund.py scenario-1-auto-approve
```

应该输出：
```
CUSTOMER REFUND PIPELINE — ADK IMPLEMENTATION
====================================================
Scenario    : scenario-1-auto-approve
Order ID    : 67890
Expected    : APPROVE — AUTO_APPROVED
====================================================

[Agent outputs...]

✓ Pipeline complete
✓ Output saved to: output/refund-demo-01/pipeline-output.json
```

---

## 查看结果

```bash
cat output/refund-demo-01/pipeline-output.json | jq '.'
```

---

## ⚠️ 安全提醒

```bash
# 验证凭证没有提交到 Git
cd /Users/fmlin/Documents/customer-refund-agent
git ls-files | grep -E "\.env|key\.json"
# 应该返回空（没有文件被追踪）

# 验证 .env 在 .gitignore 中
grep ".env" .gitignore
# 应该输出: .env
```

---

## 快速参考

| 命令 | 用途 |
|------|------|
| `gcloud auth login` | 登录 GCP（需要批准） |
| `gcloud config set project linkhealth-care-2024` | 设置默认项目 |
| `gcloud iam service-accounts create ...` | 创建服务账号 |
| `gcloud iam service-accounts keys create ...` | 下载密钥 |
| `python test_gemini.py` | 测试 Gemini API |
| `python run_refund.py scenario-1-auto-approve` | 运行退款 |

---

## 遇到问题？

### "Permission denied"
```bash
gcloud projects add-iam-policy-binding linkhealth-care-2024 \
  --member=serviceAccount:refund-agent-dev@linkhealth-care-2024.iam.gserviceaccount.com \
  --role=roles/editor
```

### "API not enabled"
```bash
gcloud services enable generativeaiapi.googleapis.com
sleep 5
python test_gemini.py
```

### "GOOGLE_APPLICATION_CREDENTIALS not found"
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/Users/fmlin/gcp-refund-agent-key.json
python test_gemini.py
```

---

**完成所有步骤后，你就能直接运行 Python 脚本调用 Gemini！** 🚀
