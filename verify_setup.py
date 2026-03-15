#!/usr/bin/env python3
"""
Shell AI Firewall - Setup Verification Script
Checks if all dependencies are installed correctly
"""

import sys

print("=" * 60)
print("Shell AI Firewall - Setup Verification")
print("=" * 60)

errors = []
warnings = []

# Check Python version
print("\n[1/10] Checking Python version...")
if sys.version_info >= (3, 13):
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
else:
    errors.append(f"❌ Python 3.13+ required, found {sys.version_info.major}.{sys.version_info.minor}")

# Check Flask
print("\n[2/10] Checking Flask...")
try:
    import flask
    print(f"✅ Flask {flask.__version__}")
except ImportError:
    errors.append("❌ Flask not installed. Run: pip install flask")

# Check Flask-JWT-Extended
print("\n[3/10] Checking Flask-JWT-Extended...")
try:
    import flask_jwt_extended
    print(f"✅ Flask-JWT-Extended installed")
except ImportError:
    errors.append("❌ Flask-JWT-Extended not installed. Run: pip install flask-jwt-extended")

# Check bcrypt
print("\n[4/10] Checking bcrypt...")
try:
    import bcrypt
    print(f"✅ bcrypt {bcrypt.__version__}")
except ImportError:
    errors.append("❌ bcrypt not installed. Run: pip install bcrypt")

# Check PyMuPDF
print("\n[5/10] Checking PyMuPDF...")
try:
    import fitz
    print(f"✅ PyMuPDF installed")
except ImportError:
    errors.append("❌ PyMuPDF not installed. Run: pip install PyMuPDF")

# Check spaCy
print("\n[6/10] Checking spaCy...")
try:
    import spacy
    print(f"✅ spaCy {spacy.__version__}")
    try:
        nlp = spacy.load("en_core_web_sm")
        print(f"✅ spaCy model 'en_core_web_sm' loaded")
    except OSError:
        warnings.append("⚠️  spaCy model 'en_core_web_sm' not found. Run: python -m spacy download en_core_web_sm")
except ImportError:
    errors.append("❌ spaCy not installed. Run: pip install spacy")

# Check sentence-transformers
print("\n[7/10] Checking sentence-transformers...")
try:
    import sentence_transformers
    print(f"✅ sentence-transformers {sentence_transformers.__version__}")
except ImportError:
    errors.append("❌ sentence-transformers not installed. Run: pip install sentence-transformers")

# Check scikit-learn
print("\n[8/10] Checking scikit-learn...")
try:
    import sklearn
    print(f"✅ scikit-learn {sklearn.__version__}")
except ImportError:
    errors.append("❌ scikit-learn not installed. Run: pip install scikit-learn")

# Check Bytez
print("\n[9/10] Checking Bytez SDK...")
try:
    import bytez
    print(f"✅ Bytez SDK installed")
except ImportError:
    errors.append("❌ Bytez SDK not installed. Run: pip install bytez")

# Check config.py
print("\n[10/10] Checking config.py...")
try:
    from config import BYTEZ_API_KEY, JWT_SECRET_KEY, DATABASE_PATH
    if BYTEZ_API_KEY and BYTEZ_API_KEY != 'your-bytez-api-key-here':
        print(f"✅ BYTEZ_API_KEY configured")
    else:
        warnings.append("⚠️  BYTEZ_API_KEY not configured in config.py")
    
    if JWT_SECRET_KEY and JWT_SECRET_KEY != 'your-secret-key-here':
        print(f"✅ JWT_SECRET_KEY configured")
    else:
        warnings.append("⚠️  JWT_SECRET_KEY not configured in config.py")
    
    print(f"✅ DATABASE_PATH: {DATABASE_PATH}")
except ImportError:
    errors.append("❌ config.py not found or has errors")
except Exception as e:
    errors.append(f"❌ Error reading config.py: {e}")

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

if errors:
    print(f"\n❌ {len(errors)} ERROR(S) FOUND:")
    for err in errors:
        print(f"  {err}")

if warnings:
    print(f"\n⚠️  {len(warnings)} WARNING(S):")
    for warn in warnings:
        print(f"  {warn}")

if not errors and not warnings:
    print("\n✅ ALL CHECKS PASSED!")
    print("\nYou're ready to run the firewall:")
    print("  1. Initialize database: python database/init_db.py")
    print("  2. Seed demo data: python database/seed.py")
    print("  3. Start server: python app.py")
    print("  4. Open browser: http://localhost:5000")
    print("  5. Login: admin/admin123")
elif not errors:
    print("\n✅ SETUP COMPLETE (with warnings)")
    print("\nYou can run the firewall, but some features may not work:")
    print("  1. Initialize database: python database/init_db.py")
    print("  2. Seed demo data: python database/seed.py")
    print("  3. Start server: python app.py")
else:
    print("\n❌ SETUP INCOMPLETE")
    print("\nPlease fix the errors above before running the firewall.")

print("\n" + "=" * 60)
