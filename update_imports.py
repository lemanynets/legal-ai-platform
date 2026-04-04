import os

root = r"c:\Users\ja\Documents\legal-ai-platform\frontend\app"

for dirpath, dirnames, filenames in os.walk(root):
    for filename in filenames:
        if filename.endswith(".tsx") or filename.endswith(".ts"):
            path = os.path.join(dirpath, filename)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            new_content = content.replace('"../../../lib/', '"@/lib/')
            new_content = new_content.replace('"../../lib/', '"@/lib/')
            
            if new_content != content:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {path}")
