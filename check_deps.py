#!/usr/bin/env python3
import importlib.util
import subprocess
import sys

def check_install_package(package, package_import=None):
    """Check if a package is installed and install if missing."""
    if package_import is None:
        package_import = package
    
    # Check if the package is already installed
    if importlib.util.find_spec(package_import) is not None:
        print(f"✓ {package} is already installed")
        return True
    
    # Try to install the package
    print(f"Installing {package}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✓ Successfully installed {package}")
        return True
    except Exception as e:
        print(f"✗ Failed to install {package}: {e}")
        return False

def main():
    """Check and install required dependencies."""
    required_packages = [
        ("pillow", "PIL"),
        ("pyopenssl", "OpenSSL"),
        ("cryptography", "cryptography")
    ]
    
    all_installed = True
    for package, package_import in required_packages:
        if not check_install_package(package, package_import):
            all_installed = False
    
    if not all_installed:
        print("\nSome dependencies failed to install. Please install them manually:")
        print("pip install pillow pyopenssl cryptography")
        sys.exit(1)
    
    # Create requirements.txt if it doesn't exist
    try:
        with open("requirements.txt", "w") as f:
            f.write("pillow\npyopenssl\ncryptography\n")
    except Exception as e:
        print(f"Warning: Could not create requirements.txt: {e}")
    
    print("\nAll dependencies are installed and ready.")
    return 0

if __name__ == "__main__":
    sys.exit(main())