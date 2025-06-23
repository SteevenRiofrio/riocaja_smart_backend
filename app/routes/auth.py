# app/routes/auth.py - CORREGIR EL ENDPOINT DE COMPLETAR PERFIL

@router.post("/complete-profile")
async def complete_profile(profile: UserProfile, user=Depends(get_current_user)):
    """Completa el perfil del usuario en su primer login"""
    user_id = user.get("sub")
    
    try:
        # VERIFICAR QUE EL USUARIO EXISTE Y ESTÁ APROBADO
        current_user = user_service.get_user_info(user_id)
        if not current_user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # VERIFICAR QUE EL USUARIO ESTÁ APROBADO Y TIENE CÓDIGO ASIGNADO
        if current_user.get("estado") != "activo":
            raise HTTPException(status_code=400, detail="Su cuenta aún no ha sido aprobada")
        
        if not current_user.get("codigo_corresponsal"):
            raise HTTPException(status_code=400, detail="No tiene un código de corresponsal asignado. Contacte al administrador.")
        
        # VERIFICAR QUE EL CÓDIGO ENVIADO COINCIDE CON EL ASIGNADO
        codigo_asignado = current_user.get("codigo_corresponsal")
        codigo_enviado = profile.codigo_corresponsal
        
        if codigo_asignado != codigo_enviado:
            raise HTTPException(
                status_code=400, 
                detail=f"El código proporcionado no coincide con el asignado. Código esperado: {codigo_asignado}"
            )
        
        # COMPLETAR EL PERFIL - SOLO ACTUALIZAR NOMBRE LOCAL Y MARCAR COMO COMPLETO
        success = user_service.complete_user_profile_simple(
            user_id=user_id,
            nombre_local=profile.nombre_local
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Error al completar perfil")
        
        return {"message": "Perfil completado correctamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en complete_profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# app/models/user.py - ACTUALIZAR EL MODELO DE PERFIL

class UserProfile(BaseModel):
    codigo_corresponsal: str  # Para verificación
    nombre_local: str
    # ELIMINAR estos campos que ya no se necesitan:
    # nombre_completo: str
    # password: str = Field(min_length=8)


# app/services/user_service.py - AGREGAR MÉTODO SIMPLIFICADO

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