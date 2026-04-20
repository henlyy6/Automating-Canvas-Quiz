# Canvas Quiz AI Solver

> Automated Canvas quiz solver with multi-AI provider fallback support

## 🚀 Quick Start

1. **CLONE & INSTALL**:
IN bash
git clone https://github.com/yourusername/canvas-quiz-ai-solver.git
cd canvas-quiz-ai-solver
pip install selenium openai google-genai

CONFIGURE:
# config section in solver.py
QUIZ_URL = "your-canvas-quiz-url"
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

GEMINI_API_KEY = "your-key"
CEREBRAS_API_KEY = "your-key"  
GROQ_API_KEY = "your-key"

RUN:
python solver.py
# Login to Canvas → Start quiz → Press Enter in terminal

📦 Requirements
Python 3.7+

Brave Browser (or modify for Chrome)

API keys from:

Google AI Studio

Cerebras Cloud

Groq Console

🔄 How It Works
Priority	Provider	Model	Role
1	Gemini	2.0 Flash	Primary
2	Cerebras	Llama 3.1 8B	Fallback
3	Groq	Llama 3.3 70B	Last resort
Process:

Extracts questions & filters invalid/placeholder choices

Queries AI providers in sequence until successful response

Fuzzy matches answer to clickable option

Auto-navigates through multi-page quizzes

⚙️ Features
Smart filtering of 4-choice questions with only 2 valid answers

Binary question optimization (yes/no, true/false)

Quota-aware - skips providers with exceeded limits

Multiple click fallback strategies

Already answered detection

⚠️ Disclaimer
Educational use only. Respect your institution's academic integrity policies and API rate limits.

📄 License
MIT
