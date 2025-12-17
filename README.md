# 🤖 AI Test Triage Agent

There are ongoing debates in the test automation community on whether failing automation scripts should be auto-healed or left for engineers to fix.

This project intentionally takes the second approach. Instead of automatically modifying tests, the AI Test Triage Agent focuses on assisting engineers by analyzing failures, reducing log-analysis effort, explaining likely root causes, and suggesting potential fixes — while keeping humans in control of code changes.

## 🎯 Problem Statement

Modern CI/CD pipelines generate numerous test failures, with many being:
- **Flaky tests** (pass on retry)
- **Environment issues** (network, config)
- **Data setup failures** (cleanup issues)

Engineers spend hours manually diagnosing these failures. This agent **automates triage** using:
- ✅ RAG (Retrieval-Augmented Generation) for historical context
- ✅ Local LLM reasoning (Ollama)
- ✅ Pattern matching and similarity search
- ✅ Confidence scoring to reduce hallucinations

## 🏗️ Architecture

```
CI Artifacts (logs, screenshots)
    ↓
Log Parser (structured extraction)
    ↓
Context Builder (RAG embeddings)
    ↓
Agent Reasoning Loop
    ├─ Classify failure type
    ├─ Calculate flakiness score
    ├─ Search similar past failures
    ├─ Generate explanation (LLM)
    └─ Suggest actions
    ↓
Triage Report (CLI/JSON)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- [Ollama](https://ollama.com) installed
- 4GB+ RAM

### Installation

```bash
# Clone the repo
git clone <your-repo>
cd ai-test-triage-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Pull Ollama model
ollama pull llama3.2
```

### Generate Sample Data

```bash
# Create sample logs and historical data
python generate_samples.py

# Load historical failures into memory
python -m agent.memory
```

### Analyze a Failure

```bash
# Single file analysis
python cli.py analyze demo/sample_ci_failures/test_login_timeout.log

# Batch analysis
python cli.py batch demo/sample_ci_failures/

# Show memory stats
python cli.py stats

# List flaky tests
python cli.py flaky --threshold 0.6
```

## 📊 Example Output

```
🤖 AI Test Triage Agent

📋 Classification
Test: test_user_login
Classification: timeout
Flaky Probability: 20%
Confidence: 80%

🔍 Root Cause Analysis
The element '#user-dashboard' exists but is hidden with display:none. 
The test waits for visibility but times out after 30s. This indicates 
the dashboard requires additional loading time or animation completion.

✅ Suggested Actions
1. Apply similar fix: Increased wait timeout to 60s and added waitForLoadState('networkidle')
2. Increase wait timeout (consider animation/loading time)
3. Add explicit wait for element state (visible/stable)

📚 Similar Past Failures:
  1. test_user_login
     Error: TimeoutError: selector '#user-dashboard' not visible
     Fix: Increased wait timeout to 60s and added waitForLoadState('networkidle')
```

## 🧠 Core Capabilities

### 1. Failure Classification
- **Timeout** - Element loading delays
- **Selector** - UI structure changes
- **Network** - API/connectivity issues
- **Data Setup** - Test data conflicts
- **Environment** - Config/dependency issues

### 2. Flakiness Detection
Calculates probability based on:
- Retry success patterns
- Historical failure frequency
- Error type characteristics
- Past resolution outcomes

### 3. Root Cause Explanation
- Natural language explanations
- References to log lines
- Context from similar failures
- Powered by local LLM (no API costs)

### 4. Actionable Suggestions
- Prioritized fix recommendations
- Learn from past resolutions
- Type-specific guidance
- Confidence-weighted actions

## 🛠️ Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python | Best ML/AI ecosystem |
| LLM | Ollama (llama3.2) | Local, fast, free |
| Embeddings | HuggingFace BGE | Local embeddings, no API |
| Vector DB | LanceDB | Fast, simple, single-file |
| RAG | LlamaIndex | Easy integration |
| CLI | Click + Rich | Beautiful terminal UI |
| Testing | Pytest | Standard Python testing |

## 📁 Project Structure

```
ai-test-triage-agent/
├── agent/
│   ├── models.py          # Data models (Failure, Resolution, etc.)
│   ├── memory.py          # RAG memory system
│   ├── tools.py           # Agent tools (search, classify, etc.)
│   └── planner.py         # Core reasoning loop
├── ingestion/
│   └── log_parser.py      # Parse CI logs
├── demo/
│   └── sample_ci_failures/  # Sample test logs
├── evals/
│   ├── golden_cases.json  # Test cases for evaluation
│   └── eval_runner.py     # Evaluation suite
├── data/                  # Vector DB storage
├── cli.py                 # Main CLI interface
├── config.py              # Configuration
└── requirements.txt
```

## 🧪 Testing & Evaluation

```bash
# Run tests
pytest

# Evaluate on golden cases
python evals/eval_runner.py

# Check accuracy metrics
python evals/eval_runner.py --report
```

## 🎓 Why This Approach Works

### vs. Naive LLM
❌ Naive: LLM alone hallucinates without context  
✅ This: RAG provides historical context and proven fixes

### vs. Simple Rules
❌ Rules: Miss patterns, brittle, need constant updates  
✅ This: Learns from past failures, adapts over time

### vs. Cloud APIs
❌ Cloud: Costs money, requires internet, slower  
✅ This: Runs locally, fast, free, private

## 🚧 Limitations

- **Log Format**: Currently supports structured logs (timestamp + level)
- **LLM Quality**: Local models less accurate than GPT-4
- **Memory Size**: Large failure history may slow searches
- **Language**: English logs only

## 🔮 Future Improvements

- [ ] Screenshot analysis (vision models)
- [ ] Slack/Teams integration
- [ ] CI/CD webhook integration
- [ ] Auto-fix PR generation
- [ ] Multi-language support
- [ ] Trend analysis dashboard

## 📈 Performance

On a typical laptop:
- **Parse log**: ~50ms
- **Search similar**: ~200ms
- **Generate explanation**: ~2s (with Ollama)
- **Total triage**: ~3s per failure

## 🤝 Contributing

```bash
# Add new failure types
# Edit: agent/models.py (FailureType enum)

# Improve classification
# Edit: agent/tools.py (classify_error_type)

# Add evaluation cases
# Edit: evals/golden_cases.json
```

## 📄 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

- LlamaIndex for RAG framework
- Ollama for local LLM inference
- HuggingFace for embedding models

---

Built with ❤️ for QA engineers tired of manual triage