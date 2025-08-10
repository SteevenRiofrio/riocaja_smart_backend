# scripts/create_test_receipts.py
"""
Generador de comprobantes sintéticos para testing RIOCAJA SMART
Crea 11 comprobantes con datos conocidos para validar OCR
Versión simplificada para Windows
"""

import os
import json
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from datetime import datetime
import random
from pathlib import Path

def create_test_receipts():
    """Función principal para crear comprobantes de prueba"""
    
    print("🧾 Generando comprobantes de prueba para RIOCAJA SMART...")
    
    # Crear directorio de salida
    output_dir = Path("tests/fixtures/receipts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Datos de bancos ecuatorianos
    banks = [
        {"key": "banco_guayaquil", "name": "BANCO DE GUAYAQUIL", "expected_accuracy": 0.92, "color": "#1565C0"},
        {"key": "banco_pacifico", "name": "BANCO DEL PACÍFICO", "expected_accuracy": 0.88, "color": "#D32F2F"},
        {"key": "produbanco", "name": "PRODUBANCO", "expected_accuracy": 0.78, "color": "#388E3C"},
        {"key": "banco_internacional", "name": "BANCO INTERNACIONAL", "expected_accuracy": 0.85, "color": "#F57C00"},
        {"key": "pichincha", "name": "BANCO PICHINCHA", "expected_accuracy": 0.90, "color": "#7B1FA2"}
    ]
    
    # Condiciones de prueba
    conditions = [
        {"name": "optimal", "description": "Condiciones óptimas", "accuracy_modifier": 1.0},
        {"name": "poor_lighting", "description": "Iluminación deficiente", "accuracy_modifier": 0.9},
        {"name": "wrinkled", "description": "Comprobante arrugado", "accuracy_modifier": 0.8},
        {"name": "faded", "description": "Impresión térmica desvanecida", "accuracy_modifier": 0.85},
        {"name": "rotated", "description": "Orientación incorrecta", "accuracy_modifier": 0.98}
    ]
    
    # Tipos de transacciones
    transaction_types = [
        "Recarga claro", "Recarga movistar", "Pago SRI", 
        "Depósito", "Retiro", "Transferencia", "Pago servicios"
    ]
    
    generated_receipts = []
    
    # Generar 11 comprobantes
    for i in range(11):
        test_id = i + 1
        bank = banks[i % len(banks)]
        condition = conditions[i % len(conditions)]
        
        print(f"📄 Generando comprobante {test_id:02d}: {bank['key']} - {condition['name']}")
        
        # Datos del comprobante (usando seed para reproducibilidad)
        random.seed(test_id)
        receipt_data = {
            "banco": bank["name"],
            "fecha": f"{random.randint(1,9):02d}/08/2025",
            "hora": f"{random.randint(10,20):02d}:{random.randint(10,59):02d}:{random.randint(10,59):02d}",
            "numero_transaccion": f"20390{test_id:04d}",
            "monto": f"{random.uniform(10.0, 150.0):.2f}",
            "tipo": random.choice(transaction_types),
            "comercio": random.choice(["Víveres Brandon", "Comercial JG", "Tienda María", "Kiosko Central"]),
            "terminal": f"T{random.randint(1000, 9999)}",
            "codigo_autorizacion": f"AUT{random.randint(100000, 999999)}"
        }
        
        # Crear imagen del comprobante
        img = create_receipt_image(bank, receipt_data, condition)
        
        # Guardar imagen
        filename = f"receipt_{test_id:02d}_{bank['key']}_{condition['name']}.jpg"
        filepath = output_dir / filename
        img.save(filepath, "JPEG", quality=85)
        
        # Calcular precisión esperada
        expected_accuracy = bank["expected_accuracy"] * condition["accuracy_modifier"]
        
        # Guardar datos esperados
        expected_file = output_dir / f"expected_{test_id:02d}.json"
        expected_data = {
            "filename": filename,
            "expected_data": receipt_data,
            "expected_accuracy": expected_accuracy,
            "bank": bank['key'],
            "condition": condition['name'],
            "test_conditions": {
                "bank": bank['key'],
                "conditions": condition['name'],
                "expected_accuracy": expected_accuracy
            }
        }
        
        with open(expected_file, 'w', encoding='utf-8') as f:
            json.dump(expected_data, f, indent=2, ensure_ascii=False)
        
        # Agregar a lista de generados
        generated_receipts.append({
            "id": test_id,
            "filename": filename,
            "bank": bank['key'],
            "condition": condition['name'],
            "expected_accuracy": expected_accuracy,
            "data": receipt_data
        })
        
        print(f"   ✅ {filename} (Precisión esperada: {expected_accuracy:.1%})")
    
    # Guardar resumen general
    summary = {
        "total_receipts": len(generated_receipts),
        "generated_at": datetime.now().isoformat(),
        "description": "Suite de comprobantes para testing OCR de RIOCAJA SMART",
        "receipts": generated_receipts
    }
    
    summary_file = output_dir / "test_suite_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎯 Generación completada:")
    print(f"   📁 Ubicación: {output_dir}")
    print(f"   📄 Total comprobantes: {len(generated_receipts)}")
    print(f"   📋 Resumen: test_suite_summary.json")
    print(f"   📊 Archivos JSON con datos esperados: {len(generated_receipts)}")
    
    return generated_receipts

def create_receipt_image(bank_info, receipt_data, condition):
    """Crear imagen del comprobante bancario"""
    
    # Dimensiones del comprobante
    width, height = 400, 600
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Intentar cargar fuentes del sistema
    try:
        title_font = ImageFont.truetype("arial.ttf", 16)
        normal_font = ImageFont.truetype("arial.ttf", 12)
        small_font = ImageFont.truetype("arial.ttf", 10)
    except:
        # Fallback a fuente por defecto si no encuentra Arial
        try:
            title_font = ImageFont.truetype("calibri.ttf", 16)
            normal_font = ImageFont.truetype("calibri.ttf", 12)
            small_font = ImageFont.truetype("calibri.ttf", 10)
        except:
            title_font = ImageFont.load_default()
            normal_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
    
    # Posición inicial
    y_pos = 20
    
    # Header del banco
    draw.text((20, y_pos), bank_info["name"], fill=bank_info["color"], font=title_font)
    y_pos += 35
    
    # Línea separadora
    draw.line([(20, y_pos), (width-20, y_pos)], fill="black", width=1)
    y_pos += 25
    
    # Título del comprobante
    title_text = "COMPROBANTE DE TRANSACCIÓN"
    # Centrar el título
    title_bbox = draw.textbbox((0, 0), title_text, font=normal_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw.text((title_x, y_pos), title_text, fill="black", font=normal_font)
    y_pos += 35
    
    # Información del comprobante
    lines = [
        f"Fecha: {receipt_data['fecha']}",
        f"Hora: {receipt_data['hora']}",
        f"Terminal: {receipt_data['terminal']}",
        f"Transacción: {receipt_data['numero_transaccion']}",
        "",
        f"Tipo: {receipt_data['tipo']}",
        f"Comercio: {receipt_data['comercio']}",
        "",
        f"MONTO: ${receipt_data['monto']}",
        "",
        f"Autorización: {receipt_data['codigo_autorizacion']}",
        "",
        "GRACIAS POR SU PREFERENCIA"
    ]
    
    # Dibujar líneas
    for line in lines:
        if line == "":
            y_pos += 12
            continue
        
        font_to_use = normal_font
        color = "black"
        
        # Formateo especial para líneas importantes
        if "MONTO:" in line:
            font_to_use = title_font
            color = bank_info["color"]
        elif line in ["COMPROBANTE DE TRANSACCIÓN", "GRACIAS POR SU PREFERENCIA"]:
            font_to_use = small_font
            # Centrar texto
            line_bbox = draw.textbbox((0, 0), line, font=font_to_use)
            line_width = line_bbox[2] - line_bbox[0]
            x_centered = (width - line_width) // 2
            draw.text((x_centered, y_pos), line, fill=color, font=font_to_use)
            y_pos += 18
            continue
        
        draw.text((20, y_pos), line, fill=color, font=font_to_use)
        y_pos += 18
    
    # Aplicar efectos según condición
    if condition["name"] == "poor_lighting":
        # Simular mala iluminación (más oscuro)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(0.7)
    elif condition["name"] == "wrinkled":
        # Simular comprobante arrugado (menos contraste)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(0.8)
    elif condition["name"] == "faded":
        # Simular impresión térmica desvanecida (más claro)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.3)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(0.6)
    elif condition["name"] == "rotated":
        # Rotar 90 grados para simular orientación incorrecta
        img = img.rotate(90, expand=True)
    
    return img

# Punto de entrada principal
if __name__ == "__main__":
    try:
        receipts = create_test_receipts()
        print(f"\n🚀 ¡Proceso completado exitosamente!")
        print(f"   Generados {len(receipts)} comprobantes para testing")
        print(f"\n📋 Siguiente paso:")
        print(f"   Ejecutar tests con: python -m pytest tests/ -v")
        
    except Exception as e:
        print(f"\n❌ Error durante la generación: {e}")
        print(f"   Verifica que tengas instalado Pillow: pip install Pillow")
        print(f"   Si persiste el error, revisa los permisos de escritura")
        import traceback
        traceback.print_exc()