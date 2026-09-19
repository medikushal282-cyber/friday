import os
import re
import json
from typing import Tuple, Optional

def remove_tool_protocol_markup(text: str) -> str:
    """
    Strips raw tool calls, tool protocol XML/JSON tags (<tool_call>...</tool_call>,
    <function=...>...</function>, <parameter=...>...</parameter>, etc.) from the text.
    """
    if not text:
        return ""

    # Strip complete <tool_call>...</tool_call> blocks (multiline)
    cleaned = re.sub(r'<tool_call\b[^>]*>.*?</tool_call>', '', text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'</?tool_call\b[^>]*>', '', cleaned, flags=re.IGNORECASE)
    # Strip complete <function=...>...</function> blocks
    cleaned = re.sub(r'<function=[^>]*>.*?</function>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'</?function\b[^>]*>', '', cleaned, flags=re.IGNORECASE)
    # Strip complete <parameter=...>...</parameter> blocks
    cleaned = re.sub(r'<parameter=[^>]*>.*?</parameter>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'</?parameter\b[^>]*>', '', cleaned, flags=re.IGNORECASE)
    # Strip <json>...</json> if wrapping function calls
    cleaned = re.sub(r'<json\b[^>]*>.*?</json>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)

    return cleaned.strip()

def extract_code_fence(text: str, ext: str) -> Optional[str]:
    """
    Extracts content from markdown code fences if present.
    Matches language identifiers corresponding to extension when possible.
    """
    if "```" not in text:
        return None

    fence_map = {
        ".py": ["python", "py"],
        ".html": ["html", "htm"],
        ".htm": ["html", "htm"],
        ".css": ["css"],
        ".json": ["json"],
        ".js": ["javascript", "js"],
        ".ts": ["typescript", "ts"],
        ".csv": ["csv"],
        ".md": ["markdown", "md"],
        ".sh": ["bash", "sh"]
    }
    target_langs = fence_map.get(ext.lower(), [])

    lines = text.splitlines()
    blocks = []
    current_block = []
    current_lang = ""
    in_fence = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_fence:
                blocks.append((current_lang, "\n".join(current_block)))
                current_block = []
                current_lang = ""
                in_fence = False
            else:
                in_fence = True
                current_lang = stripped[3:].strip().lower()
        elif in_fence:
            current_block.append(line)

    if not blocks:
        return None

    for lang, content in blocks:
        if lang in target_langs:
            return content.strip()

    for lang, content in blocks:
        if content.strip():
            return content.strip()

    return None

def extract_and_validate_artifact(rel_path: str, raw_content: str) -> Tuple[bool, str, Optional[str]]:
    """
    Extracts the clean, requested artifact content from raw LLM / tool response text,
    stripping protocol markup, conversational preambles/postambles, and wrong embedded file types.
    Performs format-specific structure validation before writing.

    Returns:
        (valid: bool, extracted_content: str, error_message: Optional[str])
    """
    if not raw_content or not str(raw_content).strip():
        return False, "", f"Raw artifact content for {rel_path} is empty"

    ext = os.path.splitext(rel_path)[1].lower()

    # Step 1: Remove tool protocol markup (<tool_call>, <function=...>, etc.)
    cleaned = remove_tool_protocol_markup(raw_content)

    # Step 2: Try code fence extraction if markdown fences exist
    fenced_content = extract_code_fence(cleaned, ext)
    if fenced_content is not None:
        candidate = fenced_content
    else:
        candidate = cleaned

    # Step 3: Extension-specific structure extraction and validation
    if ext in [".html", ".htm"]:
        valid, extracted, err = _process_html(candidate, rel_path)
    elif ext == ".css":
        valid, extracted, err = _process_css(candidate, rel_path)
    elif ext == ".json":
        valid, extracted, err = _process_json(candidate, rel_path)
    elif ext == ".py":
        valid, extracted, err = _process_python(candidate, rel_path)
    elif ext in [".js", ".ts"]:
        valid, extracted, err = _process_javascript(candidate, rel_path)
    elif ext == ".csv":
        valid, extracted, err = _process_csv(candidate, rel_path)
    else:
        # Markdown, text, and other generic files: conservative cleaning
        valid, extracted, err = _process_generic(candidate, rel_path)

    if valid and raw_content.endswith("\n") and not extracted.endswith("\n"):
        extracted += "\n"

    return valid, extracted, err


def _process_html(content: str, rel_path: str) -> Tuple[bool, str, Optional[str]]:
    # 1. Reject if unhandled tool protocol tags
    if "<tool_call" in content.lower() or "<function" in content.lower():
        return False, "", f"Extracted content for {rel_path} contains unhandled tool protocol tags."

    # 2. Extract HTML document structure if surrounded by prose
    doc_match = re.search(r'(<!DOCTYPE\s+html.*?>.*?</html>)', content, flags=re.DOTALL | re.IGNORECASE)
    if doc_match:
        html_doc = doc_match.group(1).strip()
        return True, html_doc, None

    html_match = re.search(r'(<html.*?>.*?</html>)', content, flags=re.DOTALL | re.IGNORECASE)
    if html_match:
        html_doc = html_match.group(1).strip()
        return True, html_doc, None

    # Search for HTML element tags if content contains valid element blocks
    tag_matches = list(re.finditer(r'</?[a-zA-Z1-6]+[^>]*>', content))
    if tag_matches:
        start_pos = tag_matches[0].start()
        end_pos = tag_matches[-1].end()
        extracted = content[start_pos:end_pos].strip()
        if len(extracted) > 0 and ("<" in extracted and ">" in extracted):
            first_line = extracted.splitlines()[0].strip().lower()
            conversational_prefixes = ("i'll", "i will", "sure", "here is", "let me", "i need", "i cannot", "let start")
            if not any(first_line.startswith(p) for p in conversational_prefixes):
                return True, extracted, None

    content_clean = content.strip()
    if content_clean.startswith("<") and (content_clean.endswith(">") or "</html>" in content_clean.lower()):
        return True, content_clean, None

    return False, "", f"Extracted content for {rel_path} is not valid HTML (contains prose/tool markup instead of HTML structure)."


def _process_css(content: str, rel_path: str) -> Tuple[bool, str, Optional[str]]:
    # 1. Reject if tool protocol tags
    if "<tool_call" in content.lower() or "<function" in content.lower():
        return False, "", f"Extracted content for {rel_path} contains unhandled tool protocol tags."

    # 2. Reject if content contains embedded HTML document or HTML element tags
    html_tag_pattern = r'</?(?:html|body|div|head|script|style|button|p|span|h[1-6]|a|table|tr|td|li|ul|ol|img|form|input|meta|link|doctype)\b[^>]*>'
    if re.search(html_tag_pattern, content, flags=re.IGNORECASE) or re.search(r'<!DOCTYPE\s+html', content, flags=re.IGNORECASE):
        return False, "", f"Extracted content for {rel_path} contains embedded HTML markup instead of CSS."

    # 3. Strip conversational preambles/postambles
    lines = content.splitlines()
    filtered = []
    conversational_prefixes = (
        "i'll", "i will", "sure", "here is", "here's", "to solve", "this script",
        "the following", "below is", "certainly", "let's", "first,", "let me", "i need", "i cannot"
    )
    for line in lines:
        stripped = line.strip().lower()
        if any(stripped.startswith(p) for p in conversational_prefixes):
            if not line.strip().startswith("/*") and "{" not in line:
                continue
        filtered.append(line)


    cleaned_css = "\n".join(filtered).strip()

    if not cleaned_css:
        return False, "", f"Extracted content for {rel_path} contains no valid CSS rules."

    # 4. Comprehensive CSS structure validation
    has_braces = "{" in cleaned_css and "}" in cleaned_css
    has_at_rules = cleaned_css.startswith("@") or "@media" in cleaned_css or "@keyframes" in cleaned_css or "@import" in cleaned_css
    has_comments = cleaned_css.startswith("/*") and "*/" in cleaned_css
    has_declarations = ":" in cleaned_css and ";" in cleaned_css

    if has_braces or has_at_rules or (has_comments and len(cleaned_css) > 5) or has_declarations:
        return True, cleaned_css, None

    return False, "", f"Extracted content for {rel_path} does not match CSS structure."


def _process_json(content: str, rel_path: str) -> Tuple[bool, str, Optional[str]]:
    if "<tool_call" in content.lower() or "<function" in content.lower():
        return False, "", f"Extracted content for {rel_path} contains unhandled tool protocol tags."

    start_curly = content.find("{")
    start_bracket = content.find("[")

    if start_curly == -1 and start_bracket == -1:
        return False, "", f"Extracted content for {rel_path} contains no JSON object or array."

    if start_curly != -1 and (start_bracket == -1 or start_curly < start_bracket):
        start_idx = start_curly
        end_char = "}"
        end_idx = content.rfind(end_char)
    else:
        start_idx = start_bracket
        end_char = "]"
        end_idx = content.rfind(end_char)

    if end_idx == -1 or end_idx < start_idx:
        return False, "", f"Extracted content for {rel_path} contains malformed JSON boundaries."

    json_str = content[start_idx:end_idx+1].strip()

    try:
        json.loads(json_str)
        return True, json_str, None
    except json.JSONDecodeError as e:
        return False, "", f"Extracted content for {rel_path} is invalid JSON: {str(e)}"


def _process_python(content: str, rel_path: str) -> Tuple[bool, str, Optional[str]]:
    if "<tool_call" in content.lower() or "<function" in content.lower() or "<parameter" in content.lower():
        content = remove_tool_protocol_markup(content)

    lines = content.splitlines()
    filtered = []
    conversational_prefixes = (
        "i'll start by", "i'll", "i will", "let me", "first, i'll", "first,",
        "now i need to", "now i", "insight", "here is the corrected code",
        "here is the python code", "here is", "here's", "sure,", "sure",
        "let's", "to accomplish this", "to solve", "this script", "the following",
        "below is", "certainly", "i need", "i cannot"
    )
    for line in lines:
        stripped = line.strip().lower()
        if any(stripped.startswith(p) for p in conversational_prefixes):
            if not line.strip().startswith("#") and not line.strip().startswith("import ") and not line.strip().startswith("from "):
                continue
        filtered.append(line)

    cleaned_py = "\n".join(filtered).strip()

    if not cleaned_py:
        return False, "", f"Extracted content for {rel_path} contains no valid Python code."

    try:
        compile(cleaned_py, rel_path, "exec")
        return True, cleaned_py, None
    except SyntaxError as e:
        return False, "", f"Python syntax error in extracted content for {rel_path}: {e.msg} (line {e.lineno})"
    except Exception as e:
        return False, "", f"Compilation error in extracted content for {rel_path}: {str(e)}"


def _process_javascript(content: str, rel_path: str) -> Tuple[bool, str, Optional[str]]:
    if "<tool_call" in content.lower() or "<function" in content.lower():
        return False, "", f"Extracted content for {rel_path} contains unhandled tool protocol tags."

    if "<!DOCTYPE html>" in content or "<html>" in content or "<body>" in content:
        return False, "", f"Extracted content for {rel_path} contains HTML document instead of JavaScript."

    lines = content.splitlines()
    filtered = []
    conversational_prefixes = ("i'll", "i will", "sure", "here is", "here's", "to solve", "this script", "the following", "below is", "certainly", "let's", "first,", "let me", "i need", "i cannot")
    for line in lines:
        stripped = line.strip().lower()
        if any(stripped.startswith(p) for p in conversational_prefixes):
            if not line.strip().startswith("//") and not line.strip().startswith("/*"):
                continue
        filtered.append(line)

    cleaned_js = "\n".join(filtered).strip()
    if not cleaned_js:
        return False, "", f"Extracted content for {rel_path} is empty."
    return True, cleaned_js, None


def _process_csv(content: str, rel_path: str) -> Tuple[bool, str, Optional[str]]:
    if "<tool_call" in content.lower() or "<function" in content.lower():
        return False, "", f"Extracted content for {rel_path} contains unhandled tool protocol tags."

    lines = content.splitlines()
    filtered = []
    conversational_prefixes = ("i'll", "i will", "sure", "here is", "here's", "to solve", "the following", "below is", "certainly", "let's", "first,", "let me", "i need", "i cannot")
    for line in lines:
        stripped = line.strip().lower()
        if any(stripped.startswith(p) for p in conversational_prefixes):
            if "," not in line:
                continue
        filtered.append(line)

    cleaned_csv = "\n".join(filtered).strip()
    if not cleaned_csv or "," not in cleaned_csv:
        return False, "", f"Extracted content for {rel_path} does not match CSV tabular structure."

    return True, cleaned_csv, None


def _process_generic(content: str, rel_path: str) -> Tuple[bool, str, Optional[str]]:
    if "<tool_call" in content.lower() or "<function" in content.lower():
        content = remove_tool_protocol_markup(content)

    if not content.strip():
        return False, "", f"Extracted content for {rel_path} is empty."

    return True, content.strip(), None
