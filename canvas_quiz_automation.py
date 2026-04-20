import time
import sys
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains

# ---------- Optional imports ----------
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ 'openai' not installed. Groq/Cerebras skipped.")

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ 'google-genai' not installed.")

# ---------- CONFIG ----------
QUIZ_URL = "your-canvas-quiz-url"
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

# === API KEYS ===
GEMINI_API_KEY = "key-here"
CEREBRAS_API_KEY = "key-here"
GROQ_API_KEY = "key-here"

# === Models ===
GEMINI_MODEL = "gemini-2.0-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"
CEREBRAS_MODEL = "llama3.1-8b"
# Alternative Cerebras models:
# CEREBRAS_MODEL = "qwen-2.5-32b"  # Qwen 3 235B
# CEREBRAS_MODEL = "gpt-oss-20b"   # GPT OSS
# CEREBRAS_MODEL = "glm-4-9b"      # GLM 4.7

DELAY_BETWEEN_QUESTIONS = 2
# ---------------------------

# ---------- Build AI providers ----------
clients = []
provider_models = {}

# Initialize Gemini first
if GEMINI_AVAILABLE and GEMINI_API_KEY and "YOUR" not in GEMINI_API_KEY and "key-here" not in GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        def ask_gemini(prompt):
            resp = gemini_client.models.generate_content(
                model=GEMINI_MODEL, contents=prompt,
                config={"temperature": 0.0, "max_output_tokens": 100}
            )
            return resp.text.strip()
        clients.append(("gemini", ask_gemini))
        provider_models["gemini"] = GEMINI_MODEL
        print(f"✅ Gemini ready ({GEMINI_MODEL})")
    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower():
            print(f"⚠️ Gemini quota exceeded - skipping")
        else:
            print(f"⚠️ Gemini error: {str(e)[:100]}")

# Initialize Cerebras second
if OPENAI_AVAILABLE and CEREBRAS_API_KEY and "YOUR" not in CEREBRAS_API_KEY and "key-here" not in CEREBRAS_API_KEY:
    try:
        cerebras_client = OpenAI(
            base_url="https://api.cerebras.ai/v1", 
            api_key=CEREBRAS_API_KEY
        )
        def ask_cerebras(prompt):
            resp = cerebras_client.chat.completions.create(
                model=CEREBRAS_MODEL, 
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0, 
                max_tokens=100
            )
            return resp.choices[0].message.content.strip()
        clients.append(("cerebras", ask_cerebras))
        provider_models["cerebras"] = CEREBRAS_MODEL
        print(f"✅ Cerebras ready ({CEREBRAS_MODEL})")
    except Exception as e:
        print(f"⚠️ Cerebras error: {str(e)[:100]}")
        fallback_models = ["llama3.1-8b", "llama-3.3-70b", "qwen-2.5-32b"]
        for fallback in fallback_models:
            if fallback == CEREBRAS_MODEL:
                continue
            try:
                print(f"   🔄 Trying fallback: {fallback}")
                def ask_cerebras_fallback(prompt):
                    resp = cerebras_client.chat.completions.create(
                        model=fallback, messages=[{"role": "user", "content": prompt}],
                        temperature=0.0, max_tokens=100
                    )
                    return resp.choices[0].message.content.strip()
                clients.append(("cerebras", ask_cerebras_fallback))
                provider_models["cerebras"] = fallback
                print(f"✅ Cerebras ready ({fallback})")
                break
            except:
                continue

# Initialize Groq LAST
if OPENAI_AVAILABLE and GROQ_API_KEY and "YOUR" not in GROQ_API_KEY and "key-here" not in GROQ_API_KEY:
    try:
        groq_client = OpenAI(
            base_url="https://api.groq.com/openai/v1", 
            api_key=GROQ_API_KEY
        )
        def ask_groq(prompt):
            resp = groq_client.chat.completions.create(
                model=GROQ_MODEL, 
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0, 
                max_tokens=100
            )
            return resp.choices[0].message.content.strip()
        clients.append(("groq", ask_groq))
        provider_models["groq"] = GROQ_MODEL
        print(f"✅ Groq ready ({GROQ_MODEL}) - used last")
    except Exception as e:
        print(f"⚠️ Groq error: {str(e)[:100]}")

if not clients:
    print("\n❌ No AI providers available!")
    sys.exit(1)

provider_list = [f"{name} ({provider_models[name]})" if name in provider_models else name for name, _ in clients]
print(f"📋 Providers: {provider_list}")

def ask_ai(question: str, choices: list[str]) -> str:
    prompt = (
        f"Question: {question}\n\nChoices:\n"
        + "\n".join(f"{i}. {c}" for i, c in enumerate(choices))
        + "\n\nReply with EXACTLY the text of the correct choice. No extra words, no numbering."
    )
    for i, (name, func) in enumerate(clients, 1):
        try:
            print(f"   🔄 Trying {i}/{len(clients)}: {name}...")
            ans = func(prompt)
            if ans:
                print(f"   ✅ {name} responded")
                return ans
        except Exception as e:
            print(f"   ❌ {name} failed: {str(e)[:60]}...")
            continue
    raise RuntimeError("All providers failed.")

# ---------- Text normalization ----------
def normalize_text(txt: str) -> str:
    txt = txt.strip()
    txt = re.sub(r'^\d+\.\s*', '', txt)
    txt = re.sub(r'^\([a-z]\)\s*', '', txt)
    txt = re.sub(r'\s+', ' ', txt)
    return txt

def is_valid_choice(text: str) -> bool:
    if not text or len(text.strip()) < 1:
        return False
    placeholder_patterns = [
        r'^select\s*$', r'^choose\s*$', r'^pick\s*$',
        r'^option\s*\d*$', r'^\s*$', r'^\.+$', r'^-+$',
    ]
    text_lower = text.strip().lower()
    for pattern in placeholder_patterns:
        if re.match(pattern, text_lower):
            return False
    return True

def filter_choices(choices: list[str], click_targets: list) -> tuple[list[str], list]:
    valid_choices, valid_targets = [], []
    for choice, target in zip(choices, click_targets):
        if is_valid_choice(choice):
            valid_choices.append(choice)
            valid_targets.append(target)
        else:
            print(f"   🗑️ Filtered: '{choice}'")
    return valid_choices, valid_targets

def fuzzy_match(target: str, choices: list[str]) -> int:
    norm_target = normalize_text(target)
    for i, ch in enumerate(choices):
        norm_ch = normalize_text(ch)
        if norm_target == norm_ch or norm_target in norm_ch or norm_ch in norm_target:
            return i
    
    target_lower = norm_target.lower()
    for keyword in ["yes", "no", "true", "false"]:
        if keyword in target_lower:
            for i, ch in enumerate(choices):
                if keyword in normalize_text(ch).lower():
                    return i
    
    best_idx, best_len = -1, 0
    for i, ch in enumerate(choices):
        norm_ch = normalize_text(ch)
        for j in range(1, min(len(norm_target), len(norm_ch)) + 1):
            if norm_target[:j] == norm_ch[:j] and j > best_len:
                best_len, best_idx = j, i
    return best_idx

# ---------- Selenium setup ----------
def setup_brave():
    opts = Options()
    opts.binary_location = BRAVE_PATH
    return webdriver.Chrome(options=opts)

def wait_for_quiz(driver, timeout=20):
    selectors = [".display_question", ".question", ".quiz-question"]
    start = time.time()
    while time.time() - start < timeout:
        for sel in selectors:
            if driver.find_elements(By.CSS_SELECTOR, sel):
                print(f"✅ Quiz loaded")
                return True
        time.sleep(1)
    return False

def safe_click(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.3)
        element.click()
        return True
    except:
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except:
            pass
    try:
        ActionChains(driver).move_to_element(element).click().perform()
        return True
    except:
        return False

def answer_current_page(driver):
    print("⏳ Waiting for quiz...")
    if not wait_for_quiz(driver):
        print("❌ Quiz not detected.")
        return False

    questions = driver.find_elements(By.CSS_SELECTOR, ".display_question")
    if not questions:
        questions = driver.find_elements(By.CSS_SELECTOR, ".question")
    print(f"📝 Found {len(questions)} question(s).")

    for i, q in enumerate(questions, 1):
        if q.find_elements(By.CSS_SELECTOR, "input[type='radio']:checked"):
            print(f"⏭️ Q{i} already answered.")
            continue

        try:
            q_text = q.find_element(By.CSS_SELECTOR, ".question_text").text.strip()
        except:
            q_text = q.text.split("\n")[0]

        answer_divs = q.find_elements(By.CSS_SELECTOR, ".answer") or q.find_elements(By.CSS_SELECTOR, "label")
        
        choices, click_targets = [], []
        for div in answer_divs:
            try:
                choice_text = div.find_element(By.CSS_SELECTOR, ".answer_label").text.strip()
            except:
                choice_text = div.text.strip()
            try:
                click_targets.append(div.find_element(By.TAG_NAME, "input"))
            except:
                click_targets.append(div)
            choices.append(choice_text)

        if not choices:
            print(f"⚠️ No choices for Q{i}.")
            continue

        original_count = len(choices)
        choices, click_targets = filter_choices(choices, click_targets)
        
        if not choices:
            print(f"⚠️ No valid choices for Q{i}.")
            continue
            
        if len(choices) < original_count:
            print(f"   📊 {original_count} → {len(choices)} valid choices")

        print(f"\n❓ Q{i}: {q_text[:60]}...")
        ans = ask_ai(q_text, choices)
        print(f"🤖 → {ans}")

        match_idx = fuzzy_match(ans, choices)
        if match_idx != -1:
            if safe_click(driver, click_targets[match_idx]):
                print(f"   ✅ Clicked: '{choices[match_idx]}'")
            else:
                print(f"   ❌ Click failed")
        else:
            print(f"   ❌ No match for '{ans}'")
            ans_lower = ans.lower()
            for keyword in ["yes", "no"]:
                if keyword in ans_lower:
                    for idx, ch in enumerate(choices):
                        if keyword in ch.lower():
                            safe_click(driver, click_targets[idx])
                            print(f"   ✅ Emergency click: '{ch}'")
                            break
        
        time.sleep(DELAY_BETWEEN_QUESTIONS)
    return True

def click_next_if_exists(driver):
    try:
        next_btn = driver.find_element(By.CSS_SELECTOR, "input[value='Next'], button.next-quiz")
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable(next_btn))
        safe_click(driver, next_btn)
        print("➡️ Next page")
        return True
    except:
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            if "next" in btn.text.lower():
                safe_click(driver, btn)
                print("➡️ Next page")
                return True
    return False

def submit_quiz(driver):
    try:
        btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "submit_quiz_button"))
        )
        safe_click(driver, btn)
        print("🎉 Submitted!")
        return True
    except:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            safe_click(driver, btn)
            print("🎉 Submitted!")
            return True
        except:
            return False

if __name__ == "__main__":
    driver = setup_brave()
    try:
        driver.get(QUIZ_URL)
        print("\n🔑 Log in, start quiz, then press Enter.")
        input("Press Enter...")

        page = 1
        while True:
            print(f"\n--- Page {page} ---")
            answer_current_page(driver)
            if click_next_if_exists(driver):
                page += 1
                time.sleep(3)
            else:
                print("🏁 Submitting...")
                if submit_quiz(driver):
                    break
                else:
                    input("Manual submit needed. Press Enter after.")
                    break
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        driver.quit()