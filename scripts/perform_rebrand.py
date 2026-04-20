import os

def rename_scentrix():
    search_text = "Scentrix"
    replace_text = "Scentrix"
    
    # Also handle lowercase version if likely used in env vars or slugs
    search_text_lc = "scentrix"
    replace_text_lc = "scentrix"

    target_dirs = ["backend", "frontend", "ml", "scripts", "docs"]
    target_files = ["Makefile", "docker-compose.yml", "README.md", "AGENTS.md", ".env.example"]

    count = 0
    
    # Process specific files
    for filename in target_files:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            new_content = content.replace(search_text, replace_text).replace(search_text_lc, replace_text_lc)
            if new_content != content:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {filename}")
                count += 1

    # Process directories
    for root_dir in target_dirs:
        for root, dirs, files in os.walk(root_dir):
            if ".git" in root or "node_modules" in root or "__pycache__" in root:
                continue
            for file in files:
                if file.endswith(('.py', '.md', '.ts', '.tsx', '.json', '.yml', '.yaml', '.cypher', '.css', '.html', '.txt')):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        new_content = content.replace(search_text, replace_text).replace(search_text_lc, replace_text_lc)
                        if new_content != content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            print(f"Updated {file_path}")
                            count += 1
                    except Exception as e:
                        print(f"Could not process {file_path}: {e}")

    print(f"Total files updated: {count}")

if __name__ == "__main__":
    rename_scentrix()
