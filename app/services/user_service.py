# -*- coding: utf-8 -*-
# app/services/user_service.py
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from app.config import MONGO_URI, DATABASE_NAME
from app.services.crypto_service import hash_password, verify_password

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        try:
            logger.info("Conectando a MongoDB...")
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[DATABASE_NAME]
            self.users = self.db["users"]
            logger.info("Conexión exitosa a la base de datos")
        except Exception as e:
            logger.error(f"Error al conectar a MongoDB: {e}")
            raise

    def register_user(self, nombre: str, email: str, password: str, rol: str = "lector") -> dict:
        """Registra un nuevo usuario"""
        try:
            # Verificar si el email ya existe
            if self.users.find_one({"email": email}):
                raise ValueError("El email ya está registrado")
            
            # Hash de la contraseña
            password_hash = hash_password(password)
            
            # Crear el usuario
            user_data = {
                "nombre": nombre,
                "email": email,
                "password_hash": password_hash,
                "rol": rol,
                "estado": "pendiente",
                "fecha_registro": datetime.utcnow(),
                "perfil_completo": False,
                "intentos_fallidos": 0
            }
            
            result = self.users.insert_one(user_data)
            logger.info(f"Usuario registrado: {email}")
            
            return {"message": "Usuario registrado exitosamente", "user_id": str(result.inserted_id)}
            
        except Exception as e:
            logger.error(f"Error al registrar usuario: {e}")
            raise

    def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        """Autentica un usuario"""
        try:
            user = self.users.find_one({"email": email})
            if not user:
                return None
            
            if not verify_password(password, user["password_hash"]):
                # Incrementar intentos fallidos
                self.users.update_one(
                    {"_id": user["_id"]},
                    {"$inc": {"intentos_fallidos": 1}}
                )
                return None
            
            # Reset intentos fallidos en login exitoso
            self.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"intentos_fallidos": 0}}
            )
            
            # Convertir ObjectId a string
            user["_id"] = str(user["_id"])
            
            logger.info(f"Usuario autenticado: {email}")
            return user
            
        except Exception as e:
            logger.error(f"Error en autenticación: {e}")
            return None

    def get_user_info(self, user_id: str) -> Optional[dict]:
        """Obtiene información de un usuario por ID"""
        try:
            user = self.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
                # No devolver el hash de contraseña
                user.pop("password_hash", None)
            return user
        except Exception as e:
            logger.error(f"Error al obtener usuario: {e}")
            return None

    def complete_user_profile(self, user_id: str, codigo_corresponsal: str, 
                            nombre_local: str, nombre_completo: str, nueva_password: str) -> bool:
        """Completa el perfil del usuario"""
        try:
            # Verificar que el usuario existe y está pendiente
            user = self.users.find_one({"_id": ObjectId(user_id)})
            if not user or user.get("estado") != "pendiente":
                return False
            
            # Hash de la nueva contraseña
            password_hash = hash_password(nueva_password)
            
            # Actualizar el usuario
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "codigo_corresponsal": codigo_corresponsal,
                        "nombre_local": nombre_local,
                        "nombre": nombre_completo,
                        "password_hash": password_hash,
                        "perfil_completo": True,
                        "fecha_perfil_completado": datetime.utcnow()
                    }
                }
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Perfil completado para usuario: {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al completar perfil: {e}")
            return False

    def verify_corresponsal_code(self, user_id: str, codigo: str) -> bool:
        """Verifica si un código de corresponsal es válido para el usuario"""
        try:
            # Aquí puedes implementar la lógica de validación del código
            # Por ahora, una validación simple
            if len(codigo) >= 3:
                return True
            return False
        except Exception as e:
            logger.error(f"Error al verificar código: {e}")
            return False

    def get_pending_users(self) -> List[dict]:
        """Obtiene usuarios pendientes de aprobación"""
        try:
            users = list(self.users.find({"estado": "pendiente"}).sort("fecha_registro", DESCENDING))
            
            # Convertir ObjectId a string y quitar password_hash
            for user in users:
                user["_id"] = str(user["_id"])
                user.pop("password_hash", None)
            
            return users
            
        except Exception as e:
            logger.error(f"Error al obtener usuarios pendientes: {e}")
            return []

    def approve_user(self, user_id: str, admin_id: str) -> bool:
        """Aprueba un usuario pendiente"""
        try:
            result = self.users.update_one(
                {"_id": ObjectId(user_id), "estado": "pendiente"},
                {
                    "$set": {
                        "estado": "activo",
                        "aprobado_por": ObjectId(admin_id),
                        "fecha_aprobacion": datetime.utcnow()
                    }
                }
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Usuario {user_id} aprobado por {admin_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al aprobar usuario: {e}")
            return False

    def approve_user_with_code(self, user_id: str, admin_id: str, codigo_corresponsal: str) -> bool:
        """Aprueba un usuario y le asigna un código de corresponsal"""
        try:
            # Verificar que el código no esté en uso
            existing_code = self.users.find_one({"codigo_corresponsal": codigo_corresponsal})
            if existing_code and str(existing_code["_id"]) != user_id:
                raise ValueError("El código de corresponsal ya está en uso")
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id), "estado": "pendiente"},
                {
                    "$set": {
                        "estado": "activo",
                        "codigo_corresponsal": codigo_corresponsal,
                        "aprobado_por": ObjectId(admin_id),
                        "fecha_aprobacion": datetime.utcnow()
                    }
                }
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Usuario {user_id} aprobado con código {codigo_corresponsal}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al aprobar usuario con código: {e}")
            return False

    def reject_user(self, user_id: str) -> bool:
        """Rechaza un usuario pendiente"""
        try:
            result = self.users.update_one(
                {"_id": ObjectId(user_id), "estado": "pendiente"},
                {"$set": {"estado": "rechazado"}}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Usuario {user_id} rechazado")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al rechazar usuario: {e}")
            return False

    def change_user_role(self, user_id: str, new_role: str) -> bool:
        """Cambia el rol de un usuario"""
        try:
            valid_roles = ["admin", "operador", "lector"]
            if new_role not in valid_roles:
                raise ValueError(f"Rol inválido: {new_role}")
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"rol": new_role}}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Rol del usuario {user_id} cambiado a: {new_role}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al cambiar rol: {e}")
            return False

    # MÉTODOS ADICIONALES PARA GESTIÓN COMPLETA

    def get_all_users(self) -> List[dict]:
        """Obtiene todos los usuarios del sistema (excepto passwords)"""
        try:
            # Proyección para excluir campos sensibles
            projection = {
                "password_hash": 0,  # No devolver el hash de contraseña
                "intentos_fallidos": 0  # Campo interno
            }
            
            users = list(self.users.find({}, projection).sort("fecha_registro", DESCENDING))
            
            # Convertir ObjectId a string
            for user in users:
                user["_id"] = str(user["_id"])
                if user.get("aprobado_por"):
                    user["aprobado_por"] = str(user["aprobado_por"])
            
            logger.info(f"Se obtuvieron {len(users)} usuarios en total")
            return users
            
        except Exception as e:
            logger.error(f"Error al obtener todos los usuarios: {e}")
            return []
    
    def change_user_state(self, user_id: str, new_state: str) -> bool:
        """Cambia el estado de un usuario"""
        try:
            # Validar estado
            valid_states = ["activo", "pendiente", "suspendido", "inactivo"]
            if new_state not in valid_states:
                raise ValueError(f"Estado inválido: {new_state}")
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "estado": new_state,
                        "fecha_cambio_estado": datetime.utcnow()
                    }
                }
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Estado del usuario {user_id} cambiado a: {new_state}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al cambiar estado del usuario: {e}")
            return False
    
    def search_users(self, search_term: str) -> List[dict]:
        """Busca usuarios por nombre, email, código de corresponsal, etc."""
        try:
            # Crear consulta de búsqueda con regex case-insensitive
            search_regex = {"$regex": search_term, "$options": "i"}
            
            query = {
                "$or": [
                    {"nombre": search_regex},
                    {"email": search_regex},
                    {"codigo_corresponsal": search_regex},
                    {"nombre_local": search_regex}
                ]
            }
            
            # Proyección para excluir campos sensibles
            projection = {
                "password_hash": 0,
                "intentos_fallidos": 0
            }
            
            users = list(self.users.find(query, projection).sort("nombre", 1))
            
            # Convertir ObjectId a string
            for user in users:
                user["_id"] = str(user["_id"])
                if user.get("aprobado_por"):
                    user["aprobado_por"] = str(user["aprobado_por"])
            
            logger.info(f"Búsqueda '{search_term}': {len(users)} usuarios encontrados")
            return users
            
        except Exception as e:
            logger.error(f"Error en búsqueda de usuarios: {e}")
            return []
    
    def get_user_statistics(self) -> dict:
        """Obtiene estadísticas generales de usuarios"""
        try:
            # Contar por estado
            stats_by_state = list(self.users.aggregate([
                {"$group": {"_id": "$estado", "count": {"$sum": 1}}}
            ]))
            
            # Contar por rol
            stats_by_role = list(self.users.aggregate([
                {"$group": {"_id": "$rol", "count": {"$sum": 1}}}
            ]))
            
            # Total de usuarios
            total_users = self.users.count_documents({})
            
            # Usuarios con perfil completo
            complete_profiles = self.users.count_documents({"perfil_completo": True})
            
            # Usuarios registrados hoy
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            users_today = self.users.count_documents({
                "fecha_registro": {"$gte": today_start}
            })
            
            # Usuarios registrados esta semana
            week_start = today_start - timedelta(days=7)
            users_this_week = self.users.count_documents({
                "fecha_registro": {"$gte": week_start}
            })
            
            # Formatear estadísticas por estado
            state_stats = {}
            for stat in stats_by_state:
                state_stats[stat["_id"]] = stat["count"]
            
            # Formatear estadísticas por rol
            role_stats = {}
            for stat in stats_by_role:
                role_stats[stat["_id"]] = stat["count"]
            
            result = {
                "total_usuarios": total_users,
                "perfiles_completos": complete_profiles,
                "usuarios_hoy": users_today,
                "usuarios_esta_semana": users_this_week,
                "por_estado": state_stats,
                "por_rol": role_stats,
                "porcentaje_perfiles_completos": round((complete_profiles / total_users * 100) if total_users > 0 else 0, 2)
            }
            
            logger.info(f"Estadísticas generadas: {total_users} usuarios totales")
            return result
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}")
            return {
                "total_usuarios": 0,
                "perfiles_completos": 0,
                "usuarios_hoy": 0,
                "usuarios_esta_semana": 0,
                "por_estado": {},
                "por_rol": {},
                "porcentaje_perfiles_completos": 0
            }
    
    def get_users_by_state(self, state: str) -> List[dict]:
        """Obtiene usuarios filtrados por estado específico"""
        try:
            projection = {
                "password_hash": 0,
                "intentos_fallidos": 0
            }
            
            users = list(self.users.find({"estado": state}, projection).sort("fecha_registro", DESCENDING))
            
            for user in users:
                user["_id"] = str(user["_id"])
                if user.get("aprobado_por"):
                    user["aprobado_por"] = str(user["aprobado_por"])
            
            logger.info(f"Usuarios con estado '{state}': {len(users)}")
            return users
            
        except Exception as e:
            logger.error(f"Error al obtener usuarios por estado: {e}")
            return []
    
    def get_users_by_role(self, role: str) -> List[dict]:
        """Obtiene usuarios filtrados por rol específico"""
        try:
            projection = {
                "password_hash": 0,
                "intentos_fallidos": 0
            }
            
            users = list(self.users.find({"rol": role}, projection).sort("nombre", 1))
            
            for user in users:
                user["_id"] = str(user["_id"])
                if user.get("aprobado_por"):
                    user["aprobado_por"] = str(user["aprobado_por"])
            
            logger.info(f"Usuarios con rol '{role}': {len(users)}")
            return users
            
        except Exception as e:
            logger.error(f"Error al obtener usuarios por rol: {e}")
            return []
    
    def get_recent_user_activity(self, days: int = 7) -> List[dict]:
        """Obtiene actividad reciente de usuarios en los últimos N días"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Usuarios registrados recientemente
            recent_registrations = list(self.users.find({
                "fecha_registro": {"$gte": start_date}
            }, {
                "password_hash": 0,
                "intentos_fallidos": 0
            }).sort("fecha_registro", DESCENDING))
            
            # Usuarios aprobados recientemente
            recent_approvals = list(self.users.find({
                "fecha_aprobacion": {"$gte": start_date}
            }, {
                "password_hash": 0,
                "intentos_fallidos": 0
            }).sort("fecha_aprobacion", DESCENDING))
            
            # Perfiles completados recientemente
            recent_profiles = list(self.users.find({
                "fecha_perfil_completado": {"$gte": start_date}
            }, {
                "password_hash": 0,
                "intentos_fallidos": 0
            }).sort("fecha_perfil_completado", DESCENDING))
            
            # Convertir ObjectIds
            for user_list in [recent_registrations, recent_approvals, recent_profiles]:
                for user in user_list:
                    user["_id"] = str(user["_id"])
                    if user.get("aprobado_por"):
                        user["aprobado_por"] = str(user["aprobado_por"])
            
            result = {
                "registros_recientes": recent_registrations,
                "aprobaciones_recientes": recent_approvals,
                "perfiles_completados": recent_profiles,
                "periodo_dias": days
            }
            
            logger.info(f"Actividad reciente de {days} días obtenida")
            return result
            
        except Exception as e:
            logger.error(f"Error al obtener actividad reciente: {e}")
            return {
                "registros_recientes": [],
                "aprobaciones_recientes": [],
                "perfiles_completados": [],
                "periodo_dias": days
            }
    
    def validate_user_data_integrity(self, user_id: str) -> dict:
        """Valida la integridad de los datos de un usuario"""
        try:
            user = self.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {"valid": False, "errors": ["Usuario no encontrado"]}
            
            errors = []
            warnings = []
            
            # Validaciones obligatorias
            if not user.get("nombre"):
                errors.append("Falta el nombre del usuario")
            
            if not user.get("email"):
                errors.append("Falta el email del usuario")
            
            if not user.get("password_hash"):
                errors.append("Falta el hash de contraseña")
            
            if not user.get("rol"):
                errors.append("Falta el rol del usuario")
            
            if not user.get("estado"):
                errors.append("Falta el estado del usuario")
            
            # Validaciones de consistencia
            if user.get("estado") == "activo" and not user.get("fecha_aprobacion"):
                warnings.append("Usuario activo sin fecha de aprobación")
            
            if user.get("perfil_completo") and not user.get("fecha_perfil_completado"):
                warnings.append("Perfil marcado como completo sin fecha de completado")
            
            if user.get("rol") in ["admin", "operador"] and not user.get("perfil_completo"):
                warnings.append("Admin/Operador debería tener perfil completo")
            
            # Validaciones específicas por rol
            if user.get("rol") == "lector":
                if user.get("estado") == "activo" and not user.get("codigo_corresponsal"):
                    warnings.append("Lector activo sin código de corresponsal")
                
                if user.get("perfil_completo") and not user.get("nombre_local"):
                    warnings.append("Perfil completo sin nombre de local")
            
            result = {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "user_id": user_id,
                "checked_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Validación de integridad para usuario {user_id}: {'válido' if result['valid'] else 'inválido'}")
            return result
            
        except Exception as e:
            logger.error(f"Error en validación de integridad: {e}")
            return {
                "valid": False,
                "errors": [f"Error en validación: {str(e)}"],
                "warnings": [],
                "user_id": user_id
            }
    
    def get_user_summary_for_admin(self, user_id: str) -> dict:
        """Obtiene un resumen completo del usuario para administradores"""
        try:
            user = self.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                return {}
            
            # Información básica
            user["_id"] = str(user["_id"])
            if user.get("aprobado_por"):
                user["aprobado_por"] = str(user["aprobado_por"])
            
            # Quitar información sensible
            user.pop("password_hash", None)
            
            # Agregar información calculada
            user["dias_desde_registro"] = (datetime.utcnow() - user.get("fecha_registro", datetime.utcnow())).days
            
            if user.get("fecha_aprobacion"):
                user["dias_desde_aprobacion"] = (datetime.utcnow() - user["fecha_aprobacion"]).days
            
            if user.get("fecha_perfil_completado"):
                user["dias_desde_perfil_completo"] = (datetime.utcnow() - user["fecha_perfil_completado"]).days
            
            # Validar integridad
            integrity = self.validate_user_data_integrity(user_id)
            user["integridad_datos"] = integrity
            
            logger.info(f"Resumen administrativo generado para usuario {user_id}")
            return user
            
        except Exception as e:
            logger.error(f"Error al generar resumen administrativo: {e}")
            return {}
    
    def cleanup_inactive_users(self, days_threshold: int = 90) -> dict:
        """Limpia usuarios inactivos que no han completado el registro en X días"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
            
            # Buscar usuarios pendientes antiguos
            old_pending_users = list(self.users.find({
                "estado": "pendiente",
                "fecha_registro": {"$lt": cutoff_date}
            }))
            
            # Buscar usuarios inactivos antiguos sin actividad
            old_inactive_users = list(self.users.find({
                "estado": "inactivo",
                "fecha_registro": {"$lt": cutoff_date},
                "fecha_aprobacion": None
            }))
            
            # Contar antes de eliminar
            pending_count = len(old_pending_users)
            inactive_count = len(old_inactive_users)
            
            # Eliminar usuarios pendientes antiguos
            result_pending = self.users.delete_many({
                "estado": "pendiente",
                "fecha_registro": {"$lt": cutoff_date}
            })
            
            # Eliminar usuarios inactivos antiguos
            result_inactive = self.users.delete_many({
                "estado": "inactivo",
                "fecha_registro": {"$lt": cutoff_date},
                "fecha_aprobacion": None
            })
            
            total_deleted = result_pending.deleted_count + result_inactive.deleted_count
            
            cleanup_result = {
                "usuarios_eliminados": total_deleted,
                "pendientes_eliminados": result_pending.deleted_count,
                "inactivos_eliminados": result_inactive.deleted_count,
                "umbral_dias": days_threshold,
                "fecha_corte": cutoff_date.isoformat(),
                "ejecutado_en": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Limpieza completada: {total_deleted} usuarios eliminados")
            return cleanup_result
            
        except Exception as e:
            logger.error(f"Error en limpieza de usuarios: {e}")
            return {
                "usuarios_eliminados": 0,
                "error": str(e)
            }
    
    def export_users_data(self, include_sensitive: bool = False) -> List[dict]:
        """Exporta datos de usuarios para backup (con opción de incluir datos sensibles)"""
        try:
            projection = {}
            if not include_sensitive:
                projection = {
                    "password_hash": 0,
                    "intentos_fallidos": 0
                }
            
            users = list(self.users.find({}, projection))
            
            # Convertir ObjectIds y fechas a strings para serialización
            for user in users:
                user["_id"] = str(user["_id"])
                if user.get("aprobado_por"):
                    user["aprobado_por"] = str(user["aprobado_por"])
                
                # Convertir fechas a ISO string
                date_fields = ["fecha_registro", "fecha_aprobacion", "fecha_perfil_completado", "fecha_cambio_estado"]
                for field in date_fields:
                    if user.get(field):
                        user[field] = user[field].isoformat()
            
            logger.info(f"Exportación de {len(users)} usuarios completada (sensible: {include_sensitive})")
            return users
            
        except Exception as e:
            logger.error(f"Error en exportación de usuarios: {e}")
            return []
         
         
           
    def complete_user_profile_simple(self, user_id: str, nombre_local: str) -> bool:
    """Completa el perfil del usuario SIN cambiar contraseña"""
    try:
        # Verificar que el usuario existe
        user = self.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return False
        
        # Actualizar solo el nombre local y marcar perfil como completo
        result = self.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "nombre_local": nombre_local,
                    "perfil_completo": True,
                    "fecha_perfil_completado": datetime.utcnow()
                }
            }
        )
        
        success = result.modified_count > 0
        if success:
            logger.info(f"Perfil completado para usuario: {user_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error al completar perfil: {e}")
        return False   