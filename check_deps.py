import os
import ast
import sys
import stdlib_list

# Map import names to package names (if different)
PACKAGE_MAPPING = {
    "PIL": "pillow",
    "jose": "python-jose",
    "jwt": "pyjwt",
    "dotenv": "python-dotenv",
    "cv2": "opencv-python",
    "vips": "pyvips", # python binding often imported as something else? checked docs: import pyvips
    "b2sdk": "b2sdk",
    "google.oauth2": "google-auth",
    "google": "google-auth", # simplistic mapping
    "bs4": "beautifulsoup4",
}

def get_stdlib():
    try:
        return set(stdlib_list.stdlib_list("3.11"))
    except:
        return set(sys.builtin_module_names)

def get_installed_reqs(req_file):
    with open(req_file) as f:
        lines = f.readlines()
    reqs = set()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # simplistic parsing of requirements.txt
        pkg = line.split("==")[0].split(">=")[0].split("[")[0].lower()
        reqs.add(pkg)
    return reqs

def find_imports(root_dir):
    imports = set()
    for root, _, files in os.walk(root_dir):
        if "venv" in root or "__pycache__" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r") as f:
                        tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports.add(alias.name.split('.')[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imports.add(node.module.split('.')[0])
                except Exception as e:
                    print(f"Error parsing {path}: {e}")
    return imports

def main():
    root = "./backend"
    req_file = "./backend/requirements.txt"
    
    code_imports = find_imports(root)
    reqs = get_installed_reqs(req_file)
    stdlib = get_stdlib()
    
    missing = []
    
    # Filter imports
    for imp in code_imports:
        if imp.startswith("app"): continue # local app
        if imp.startswith("."): continue # relative
        if imp in stdlib: continue # standard lib
        if imp in ["tests", "alembic"]: continue # test/migration utils
        
        # Check mapping or direct name
        pkg_name = PACKAGE_MAPPING.get(imp, imp).lower()
        
        # Special cases handling
        if pkg_name == "vips": pkg_name = "pyvips"
        
        if pkg_name not in reqs:
            # Check if it's installed as a sub-dependency or slightly different name
            # This is a heuristic check
            missing.append(f"{imp} (mapped to {pkg_name})")

    if missing:
        print("Potential missing dependencies:")
        for m in missing:
            print(f" - {m}")
    else:
        print("No missing dependencies found!")

if __name__ == "__main__":
    main()
