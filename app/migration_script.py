# migration_script.py - EJECUTAR UNA SOLA VEZ PARA USUARIOS EXISTENTES

import asyncio
import logging
from datetime import datetime
from app.database import init_database, get_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_users_terms():
    """
    Script de migración para agregar campo acepto_terminos=False 
    a todos los usuarios existentes que no lo tienen
    """
    print("🔄 Iniciando migración de términos para usuarios existentes...")
    
    try:
        # Inicializar conexión a la base de datos
        if not init_database():
            print("❌ Error conectando a la base de datos")
            return False
        
        db = get_database()
        users_collection = db.users
        
        # Encontrar usuarios sin el campo acepto_terminos
        users_without_terms = list(users_collection.find({
            "acepto_terminos": {"$exists": False}
        }))
        
        print(f"📊 Encontrados {len(users_without_terms)} usuarios sin campo acepto_terminos")
        
        if len(users_without_terms) == 0:
            print("✅ Todos los usuarios ya tienen el campo acepto_terminos")
            return True
        
        # Mostrar usuarios que se van a actualizar
        print("\n👥 Usuarios que se actualizarán:")
        for user in users_without_terms:
            print(f"  - {user.get('nombre', 'Sin nombre')} ({user.get('email', 'Sin email')})")
        
        # Confirmar migración
        confirm = input(f"\n⚠️ ¿Desea continuar con la migración de {len(users_without_terms)} usuarios? (s/N): ")
        if confirm.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
            print("❌ Migración cancelada por el usuario")
            return False
        
        # Ejecutar migración
        result = users_collection.update_many(
            {"acepto_terminos": {"$exists": False}},
            {
                "$set": {
                    "acepto_terminos": False,  # ⚠️ IMPORTANTE: False para que aparezca el modal
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        print(f"✅ Migración completada exitosamente!")
        print(f"📈 {result.modified_count} usuarios actualizados")
        print(f"📋 Ahora todos los usuarios existentes tendrán acepto_terminos=False")
        print(f"🔔 La próxima vez que inicien sesión, verán el modal de términos")
        
        return True
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        logger.error(f"Error en migración: {e}")
        return False

async def verify_migration():
    """
    Verificar que la migración se ejecutó correctamente
    """
    print("\n🔍 Verificando migración...")
    
    try:
        db = get_database()
        users_collection = db.users
        
        # Contar usuarios por estado de términos
        total_users = users_collection.count_documents({})
        users_without_field = users_collection.count_documents({"acepto_terminos": {"$exists": False}})
        users_accepted = users_collection.count_documents({"acepto_terminos": True})
        users_not_accepted = users_collection.count_documents({"acepto_terminos": False})
        
        print(f"📊 RESUMEN POST-MIGRACIÓN:")
        print(f"  📋 Total de usuarios: {total_users}")
        print(f"  ❌ Sin campo acepto_terminos: {users_without_field}")
        print(f"  ✅ Términos aceptados: {users_accepted}")
        print(f"  ⏳ Términos NO aceptados: {users_not_accepted}")
        
        if users_without_field == 0:
            print("✅ Migración verificada: Todos los usuarios tienen el campo acepto_terminos")
        else:
            print("⚠️ Atención: Algunos usuarios aún no tienen el campo acepto_terminos")
        
    except Exception as e:
        print(f"❌ Error verificando migración: {e}")

async def main():
    """
    Función principal del script de migración
    """
    print("=" * 60)
    print("🛠️  SCRIPT DE MIGRACIÓN - TÉRMINOS Y CONDICIONES")
    print("=" * 60)
    
    # Ejecutar migración
    migration_success = await migrate_users_terms()
    
    if migration_success:
        # Verificar migración
        await verify_migration()
        print("\n🎉 ¡Migración completada exitosamente!")
        print("📝 PRÓXIMOS PASOS:")
        print("  1. Los usuarios existentes verán el modal de términos al iniciar sesión")
        print("  2. Los nuevos usuarios aceptan términos durante el registro")
        print("  3. Solo usuarios con acepto_terminos=True pueden usar la app")
    else:
        print("\n❌ La migración falló. Revise los logs para más detalles.")

if __name__ == "__main__":
    asyncio.run(main())