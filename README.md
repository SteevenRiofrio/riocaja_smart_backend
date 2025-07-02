# RíoCaja Smart

Sistema integral de gestión de comprobantes para Corresponsales No Bancarios (CNB) del Banco del Barrio - Banco Guayaquil.

## ������ Descripción

RíoCaja Smart es una aplicación móvil desarrollada en Flutter que permite a los corresponsales bancarios digitalizar, gestionar y generar reportes de sus transacciones diarias mediante el escaneo automático de comprobantes usando tecnología OCR.

### ✨ Características Principales

- ������ **Escaneo OCR**: Reconocimiento automático de texto en comprobantes
- ������ **Gestión de Transacciones**: Control completo de retiros, depósitos, pagos y recargas
- ������ **Reportes Automáticos**: Generación de reportes de cierre diarios en PDF
- ������ **Sistema Multi-usuario**: Roles diferenciaasesorin, Operador, cnb)
- ������ **Autenticación Segura**: Sistema de login con verificación de perfiles
- ������ **Sistema de Mensajes**: Comunicación entre administradores y usuarios
- ������ **Interfaz Intuitiva**: Diseño en español optimizado para uso móvil

## ������ Tecnologías Utilizadas

### Frontend (Aplicación Móvil)
- **Flutter 3.7+** - Framework de desarrollo multiplataforma
- **Dart** - Lenguaje de programación
- **Provider** - Gestión de estado
- **Google ML Kit** - Reconocimiento de texto OCR
- **Camera Plugin** - Acceso a cámara del dispositivo
- **HTTP** - Comunicación con API REST
- **PDF Generation** - Generación de reportes en PDF
- **Share Plus** - Compartir archivos y reportes

### Backend (API REST)
- **Python 3.8+** - Lenguaje del servidor
- **FastAPI** - Framework web moderno y rápido
- **MongoDB** - Base de datos NoSQL
- **PyMongo** - Driver de MongoDB para Python
- **Pydantic** - Validación de datos
- **JWT** - Autenticación por tokens
- **Uvicorn** - Servidor ASGI
- **Passlib + Bcrypt** - Encriptación de contraseñas

## ������ Requisitos del Sistema

### Para el Frontend (Flutter)
- Flutter SDK ≥ 3.7.2
- Dart SDK ≥ 3.7.2
- Android Studio / VS Code
- Dispositivo Android 5.0+ (API 21+) o iOS 11.0+

### Para el Backend (Python)
- Python 3.8+
- MongoDB 4.4+
- Pip (gestor de paquetes)

## ������️ Instalación y Configuración

### 1. Clonar el Repositorio
```bash
git clone https://github.com/tu-usuario/riocaja-smart.git
cd riocaja-smart
```

### 2. Configuración del Backend

#### Instalar Dependencias
```bash
# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

#### Configurar Variables de Entorno
```bash
# Crear archivo .env en la raíz del proyecto
MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net/riocaja_smart
DATABASE_NAME=riocaja_smart
SECRET_KEY=tu-clave-super-secreta
```

#### Iniciar el Servidor
```bash
# OPCIÓN A: Comando simple
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# OPCIÓN B: Con screen (recomendado para producción)
screen -S riocaja_server
cd /ruta/a/tu/proyecto
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Para salir del screen sin cerrar: Ctrl+A, luego D
# Para volver al screen: screen -r riocaja_server
# Para ver sesiones activas: screen -ls
# Para detener el servidor: screen -S riocaja_server -X quit
```

### 3. Configuración del Frontend

#### Instalar Dependencias de Flutter
```bash
cd riocaja_smart  # Directorio del proyecto Flutter
flutter pub get
```

#### Configurar IP del Servidor
Actualizar la IP del servidor en los siguientes archivos:

**lib/services/api_service.dart:**
```dart
String baseUrl = 'http://34.63.192.239:8080/api/v1';
```

**lib/services/auth_service.dart:**
```dart
String baseUrl = 'http://34.63.192.239:8080/api/v1';
```

**lib/services/admin_service.dart:**
```dart
String baseUrl = 'http://34.63.192.239:8080/api/v1/auth';
```

**lib/services/message_service.dart:**
```dart
String baseUrl = 'http://34.63.192.239:8080/api/v1/messages';
```

#### Ejecutar la Aplicación
```bash
# Limpiar cache
flutter clean
flutter pub get

# Ejecutar en modo debug
flutter run

# Generar APK para Android
flutter build apk --release
```

## ������ Uso del Sistema

### Roles de Usuario

#### ������‍������ Administrador
- Aprobar/rechazar nuevos usuarios
- Asignar códigos de corresponsal
- Gestionar roles de usuarios
- Crear y administrar mensajes del sistema
- Acceso completo a todos los comprobantes y reportes

#### ���asesorador
- Crear mensajes del sistema
- Ver usuarios pendientes
- Acceso a reportes y comprobantes (limitado)

#### ������ cnb (Corresponsal)
- Escanear y gestionar comprobantes
- Generar reportes de cierre diarios
- Ver mensajes del sistema
- Acceso solo a sus propios comprobantes

### Flujo de Trabajo Típico

1. **Registro**: El corresponsal se registra en la app
2. **Aprobación**: Un administrador aprueba la cuenta y asigna código
3. **Completar Perfil**: El usuario completa su perfil con información del local
4. **Escaneo**: Captura comprobantes con la cámara
5. **Verificación**: Revisa y confirma los datos extraídos por OCR
6. **Gestión**: Consulta historial y filtra transacciones
7. **Reportes**: Genera reportes de cierre al final del día

## ������ Endpoints de la API

### Autenticación
- `POST /api/v1/auth/register` - Registro de usuarios
- `POST /api/v1/auth/login` - Inicio de sesión
- `GET /api/v1/auth/me` - Información del usuario actual
- `POST /api/v1/auth/complete-profile` - Completar perfil

### Administración
- `GET /api/v1/auth/pending-users` - Usuarios pendientes
- `POST /api/v1/auth/approve-user-with-code` - Aprobar usuario con código
- `POST /api/v1/auth/change-role` - Cambiar rol de usuario

### Comprobantes
- `GET /api/v1/receipts/` - Obtener comprobantes
- `POST /api/v1/receipts/` - Crear comprobante
- `GET /api/v1/receipts/date/{date}` - Comprobantes por fecha
- `GET /api/v1/receipts/report/{date}` - Reporte de cierre
- `DELETE /api/v1/receipts/{transaction_number}` - Eliminar comprobante

### Mensajes
- `GET /api/v1/messages/` - Obtener mensajes
- `POST /api/v1/messages/create` - Crear mensaje
- `POST /api/v1/messages/mark-read` - Marcar como leído

## ������ Comandos de Gestión del Servidor

### Iniciar con Screen
```bash
# Crear nueva sesión
screen -S riocaja_server

# Dentro de la sesión
cd /ruta/a/tu/proyecto
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Gestionar Sesiones Screen
```bash
# Ver sesiones activas
screen -ls

# Conectar a sesión existente
screen -r riocaja_server

# Salir sin cerrar (desde dentro): Ctrl+A, luego D

# Detener sesión completamente
screen -S riocaja_server -X quit
```

### Verificación del Sistema
```bash
# Verificar que el servidor responde
curl http://34.63.192.239:8080/

# Ver documentación de la API
curl http://34.63.192.239:8080/docs

# Verificar puerto en uso
netstat -tlnp | grep :8080
```

## ������ Solución de Problemas

### Problemas Comunes

#### Error de Conexión en la App
1. Verificar que el servidor esté ejecutándose: `curl http://34.63.192.239:8080/`
2. Comprobar la IP en los archivos de configuración de Flutter
3. Verificar conectividad de red del dispositivo

#### Error de Autenticación
1. Verificar que la base de datos MongoDB esté disponible
2. Comprobar las variables de entorno (.env)
3. Verificar que el token JWT no haya expirado

#### Problemas con OCR
1. Asegurar buena iluminación al capturar
2. Mantener el comprobante dentro del marco
3. Verificar que Google ML Kit esté correctamente instalado

### Logs y Debugging

#### Ver logs del servidor
```bash
# Con screen activo
screen -r riocaja_server

# Logs de uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload --log-level debug
```

#### Debug en Flutter
```bash
# Ejecutar con logs detallados
flutter run --verbose

# Ver logs del dispositivo
flutter logs
```

## ������ Contribución

### Estructura del Proyecto
```
riocaja-smart/
├── app/                    # Backend (Python/FastAPI)
│   ├── models/            # Modelos de datos
│   ├── routes/            # Rutas de la API
│   ├── services/          # Lógica de negocio
│   └── main.py            # Punto de entrada
├── lib/                   # Frontend (Flutter)
│   ├── models/            # Modelos de datos
│   ├── providers/         # Gestión de estado
│   ├── screens/           # Pantallas de la app
│   ├── services/          # Servicios de API
│   └── widgets/           # Componentes reutilizables
├── requirements.txt       # Dependencias Python
├── pubspec.yaml          # Dependencias Flutter
└── README.md             # Este archivo
```

### Cómo Contribuir
1. Fork el repositorio
2. Crear una rama para la nueva funcionalidad
3. Hacer commits con mensajes descriptivos
4. Enviar Pull Request con descripción detallada

## ������ Licencia

Este proyecto está licenciado bajo los términos de la [Licencia MIT](LICENSE).

## ������ Soporte

Para reportar bugs o solicitar nuevas funcionalidades, por favor crear un issue en el repositorio de GitHub.

### Información de Contacto
- **Proyecto**: RíoCaja Smart
- **Banco**: Banco del Barrio - Banco Guayaquil
- **Versión**: 1.0.0

---

**Nota**: Este sistema está diseñado específicamente para corresponsales bancarios del Banco del Barrio. Para uso en producción, asegurar configuraciones de seguridad apropiadas y certificados SSL válidos.