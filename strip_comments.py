"""Remove code comments from the website files (HTML, CSS, JavaScript).
Usage (PowerShell, project root):   python strip_comments.py frontend
Optional: add more folders, e.g.    python strip_comments.py frontend backend
Safety: commit first (git add . ; git commit). Every JavaScript file is checked with `node --check` after editing and restored if the check fails.
Only comments are removed; strings, template literals, regular expressions and URLs such as https://example.com are left untouched."""
import os, re, subprocess, sys

KEYWORDS = re.compile(r"(?:return|typeof|case|in|of|delete|void|throw|new)\s*$")

def drop_blank_comment_line(out, tail_ok):
    """If the comment sat alone on its line, delete that whole line (indent and newline)."""
    text = "".join(out); line_start = text.rfind("\n") + 1
    if tail_ok and text[line_start:].strip() == "":
        return [text[:line_start]], True
    return out, False

def strip_js(src):
    out, i, n, removed = [], 0, len(src), 0
    while i < n:
        c, nx = src[i], src[i + 1] if i + 1 < n else ""
        if c in "\"'":                                   # string literal
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(src[i:j + 1]); i = j + 1; continue
        if c == "`":                                     # template literal (copied verbatim, including nested templates)
            j, depth = i + 1, 0
            while j < n:
                if src[j] == "\\": j += 2; continue
                if src[j] == "`" and depth == 0: break
                if src[j:j + 2] == "${": depth += 1; j += 2; continue
                if src[j] == "}" and depth > 0: depth -= 1
                elif src[j] == "`" and depth > 0:
                    k = j + 1
                    while k < n and src[k] != "`": k += 2 if src[k] == "\\" else 1
                    j = k
                j += 1
            out.append(src[i:j + 1]); i = j + 1; continue
        if c == "/" and nx == "/":                       # line comment
            j = src.find("\n", i); j = n if j == -1 else j
            out, whole = drop_blank_comment_line(out, True)
            if not whole: out = ["".join(out).rstrip(" \t")]            # no stray space before the removed comment
            i = j + 1 if whole and j < n else j; removed += 1; continue
        if c == "/" and nx == "*":                       # block comment
            j = src.find("*/", i + 2); j = n if j == -1 else j + 2
            rest_end = src.find("\n", j); rest_end = n if rest_end == -1 else rest_end
            out, whole = drop_blank_comment_line(out, src[j:rest_end].strip() == "")
            i = rest_end + 1 if whole and rest_end < n else j; removed += 1; continue
        if c == "/":                                     # regular expression literal or division?
            tail = "".join(out)[-40:].rstrip()
            if tail == "" or tail[-1] in "(,=:[!&|?{};+-*%<>~^" or KEYWORDS.search(tail):
                j, in_class = i + 1, False
                while j < n and (src[j] != "/" or in_class) and src[j] != "\n":
                    if src[j] == "\\": j += 1
                    elif src[j] == "[": in_class = True
                    elif src[j] == "]": in_class = False
                    j += 1
                out.append(src[i:j + 1]); i = j + 1; continue
        out.append(c); i += 1
    return "".join(out), removed

def strip_css(src):
    n = len(re.findall(r"/\*.*?\*/", src, flags=re.S))
    src = re.sub(r"^[ \t]*/\*.*?\*/[ \t]*\r?\n", "", src, flags=re.S | re.M)       # comment alone on its line(s)
    return re.sub(r"/\*.*?\*/", "", src, flags=re.S), n

def strip_html(src):
    n = len(re.findall(r"<!--.*?-->", src, flags=re.S))
    src = re.sub(r"^[ \t]*<!--.*?-->[ \t]*\r?\n", "", src, flags=re.S | re.M)
    return re.sub(r"<!--.*?-->", "", src, flags=re.S), n

def node_ok(path):
    try: return subprocess.run(["node", "--check", path], capture_output=True).returncode == 0
    except FileNotFoundError: return True                                              # node not installed: skip the check

def main(folders):
    total = 0
    for folder in folders:
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git")]
            for f in files:
                p, ext = os.path.join(root, f), os.path.splitext(f)[1].lower()
                fn = {".js": strip_js, ".css": strip_css, ".html": strip_html}.get(ext)
                if not fn: continue
                with open(p, encoding="utf-8", newline="") as h: old = h.read()
                new, n = fn(old)
                if n == 0: continue
                with open(p, "w", encoding="utf-8", newline="") as h: h.write(new)
                if ext == ".js" and not node_ok(p):
                    with open(p, "w", encoding="utf-8", newline="") as h: h.write(old)
                    print(f"RESTORED (check failed, nothing changed): {p}"); continue
                total += n; print(f"{n:3d} comment(s) removed: {p}")
    print(f"Done. {total} comment(s) removed in total.")

if __name__ == "__main__": main(sys.argv[1:] or ["frontend"])
