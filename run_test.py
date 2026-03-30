import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
    cwd="D:\\Projects\\Python\\financial-report-ai-assistant",
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace"
)

# 只打印最后 50 行
lines = result.stdout.split("\n")
for line in lines[-50:]:
    try:
        print(line)
    except:
        print(line.encode("ascii", errors="replace").decode())

print("\n=== RETURN CODE ===")
print(result.returncode)
