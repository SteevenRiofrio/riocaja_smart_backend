# test_bcrypt.py - Script para verificar funcionamiento de bcrypt
import logging
logging.basicConfig(level=logging.INFO)

try:
    from app.utils.security import hash_password, verify_password
    
    # Probar hashing y verificación
    test_password = "test123"
    print("🔍 Probando bcrypt...")
    
    # Hash password
    hashed = hash_password(test_password)
    print(f"✅ Password hasheado: {hashed[:50]}...")
    
    # Verificar password
    is_valid = verify_password(test_password, hashed)
    print(f"✅ Verificación correcta: {is_valid}")
    
    # Verificar password incorrecto
    is_invalid = verify_password("wrong_password", hashed)
    print(f"✅ Verificación incorrecta: {is_invalid}")
    
    print("🎉 Bcrypt funciona correctamente!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
