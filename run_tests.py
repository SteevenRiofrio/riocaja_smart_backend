# run_tests.py - COPIAR Y PEGAR ESTE ARCHIVO COMPLETO

import subprocess
import sys
import os
from datetime import datetime

def print_header():
    """Imprime header bonito para los tests"""
    print("=" * 60)
    print("🧪 RIOCAJA SMART - SISTEMA DE PRUEBAS")
    print("=" * 60)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print("=" * 60)

def run_command(command, description):
    """Ejecuta un comando y maneja errores"""
    print(f"\n🔄 {description}")
    print(f"💻 Comando: {command}")
    print("-" * 40)
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=300  # 5 minutos timeout
        )
        
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("⚠️ Warnings/Errores:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} - EXITOSO")
        else:
            print(f"❌ {description} - FALLÓ (código: {result.returncode})")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT: {description} tardó más de 5 minutos")
        return False
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return False

def check_dependencies():
    """Verifica que las dependencias estén instaladas"""
    print("\n🔍 VERIFICANDO DEPENDENCIAS...")
    
    required_packages = [
        "pytest",
        "pytest-cov", 
        "pytest-asyncio",
        "httpx"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package} - Instalado")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - NO instalado")
    
    if missing_packages:
        print(f"\n⚠️ INSTALANDO DEPENDENCIAS FALTANTES: {', '.join(missing_packages)}")
        install_cmd = f"pip install {' '.join(missing_packages)}"
        return run_command(install_cmd, "Instalando dependencias")
    
    print("✅ Todas las dependencias están instaladas")
    return True

def check_test_directory():
    """Verifica que el directorio tests existe"""
    if not os.path.exists("tests"):
        print("📁 Creando directorio tests...")
        os.makedirs("tests")
        
        # Crear __init__.py si no existe
        init_file = "tests/__init__.py"
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("# Tests para RioCaja Smart Backend\n")
            print("✅ Creado tests/__init__.py")
    
    # Contar archivos de prueba
    test_files = [f for f in os.listdir("tests") if f.startswith("test_") and f.endswith(".py")]
    print(f"📊 Archivos de prueba encontrados: {len(test_files)}")
    
    for test_file in test_files:
        print(f"   📄 {test_file}")
    
    return len(test_files) > 0

def run_tests():
    """Ejecuta las pruebas principales"""
    print("\n🚀 EJECUTANDO PRUEBAS...")
    
    # Comando básico de pytest
    basic_cmd = "pytest tests/ -v"
    success1 = run_command(basic_cmd, "Ejecutando pruebas básicas")
    
    if not success1:
        print("\n⚠️ Las pruebas básicas fallaron, pero continuamos...")
    
    # Comando de cobertura
    coverage_cmd = "pytest --cov=app tests/ --cov-report=term --cov-report=html"
    success2 = run_command(coverage_cmd, "Ejecutando pruebas con cobertura")
    
    return success1 or success2

def generate_coverage_report():
    """Genera y muestra reporte de cobertura"""
    print("\n📊 GENERANDO REPORTE DE COBERTURA...")
    
    # Comando para generar reporte detallado
    report_cmd = "pytest --cov=app tests/ --cov-report=term-missing --cov-report=html --cov-fail-under=0"
    success = run_command(report_cmd, "Generando reporte detallado")
    
    if success:
        print("\n📋 INFORMACIÓN DEL REPORTE:")
        print("   🌐 Reporte HTML: htmlcov/index.html")
        print("   📁 Para ver: abrir htmlcov/index.html en el navegador")
        
        # Intentar extraer el porcentaje de cobertura
        try:
            if os.path.exists("htmlcov/index.html"):
                print("✅ Reporte HTML generado exitosamente")
            else:
                print("⚠️ Reporte HTML no encontrado")
        except Exception as e:
            print(f"⚠️ Error verificando reporte: {e}")

def print_summary():
    """Imprime resumen final"""
    print("\n" + "=" * 60)
    print("📈 RESUMEN DE EJECUCIÓN")
    print("=" * 60)
    
    # Contar archivos de prueba
    if os.path.exists("tests"):
        test_files = [f for f in os.listdir("tests") if f.startswith("test_") and f.endswith(".py")]
        print(f"📊 Total archivos de prueba: {len(test_files)}")
    
    print("💡 PRÓXIMOS PASOS:")
    print("   1. Revisar el reporte HTML en htmlcov/index.html")
    print("   2. Agregar más pruebas para aumentar cobertura")
    print("   3. Ejecutar: python run_tests.py para probar nuevamente")
    
    print("\n🎯 META: Llegar al 80% de cobertura")
    print("=" * 60)

def main():
    """Función principal"""
    print_header()
    
    # 1. Verificar dependencias
    if not check_dependencies():
        print("❌ Error en dependencias. Abortando.")
        sys.exit(1)
    
    # 2. Verificar directorio de pruebas
    if not check_test_directory():
        print("⚠️ No se encontraron archivos de prueba")
        print("💡 Crea archivos test_*.py en la carpeta tests/")
        
        # Crear un archivo de prueba de ejemplo si no existe ninguno
        example_test = """# tests/test_example.py - Ejemplo básico
import pytest

def test_basic_example():
    \"\"\"Prueba de ejemplo básica\"\"\"
    assert 1 + 1 == 2

def test_string_operations():
    \"\"\"Prueba operaciones con strings\"\"\"
    text = "RioCaja Smart"
    assert "RioCaja" in text
    assert len(text) > 5
"""
        
        with open("tests/test_example.py", "w") as f:
            f.write(example_test)
        print("📝 Creado tests/test_example.py como ejemplo")
    
    # 3. Ejecutar pruebas
    if not run_tests():
        print("❌ Las pruebas fallaron")
        # No salir, continuar con el reporte
    
    # 4. Generar reporte
    generate_coverage_report()
    
    # 5. Mostrar resumen
    print_summary()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Ejecución interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 ERROR INESPERADO: {e}")
        sys.exit(1)