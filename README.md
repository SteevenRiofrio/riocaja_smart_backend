# R√≠oCaja Smart

Sistema integral de gesti√≥n de comprobantes para Corresponsales No Bancarios (CNB) del Banco del Barrio - Banco Guayaquil.

## Ì†ΩÌ≥± Descripci√≥n

R√≠oCaja Smart es una aplicaci√≥n m√≥vil desarrollada en Flutter que permite a los corresponsales bancarios digitalizar, gestionar y generar reportes de sus transacciones diarias mediante el escaneo autom√°tico de comprobantes usando tecnolog√≠a OCR.

### ‚ú® Caracter√≠sticas Principales

- Ì†ΩÌ¥ç **Escaneo OCR**: Reconocimiento autom√°tico de texto en comprobantes
- Ì†ΩÌ≥ä **Gesti√≥n de Transacciones**: Control completo de retiros, dep√≥sitos, pagos y recargas
- Ì†ΩÌ≥à **Reportes Autom√°ticos**: Generaci√≥n de reportes de cierre diarios en PDF
- Ì†ΩÌ±• **Sistema Multi-usuario**: Roles diferenciados (Admin, Operador, Lector)
- Ì†ΩÌ¥ê **Autenticaci√≥n Segura**: Sistema de login con verificaci√≥n de perfiles
- Ì†ΩÌ≤¨ **Sistema de Mensajes**: Comunicaci√≥n entre administradores y usuarios
- Ì†ΩÌ≥± **Interfaz Intuitiva**: Dise√±o en espa√±ol optimizado para uso m√≥vil

## Ì†ΩÌ∫Ä Tecnolog√≠as Utilizadas

### Frontend (Aplicaci√≥n M√≥vil)
- **Flutter 3.7+** - Framework de desarrollo multiplataforma
- **Dart** - Lenguaje de programaci√≥n
- **Provider** - Gesti√≥n de estado
- **Google ML Kit** - Reconocimiento de texto OCR
- **Camera Plugin** - Acceso a c√°mara del dispositivo
- **HTTP** - Comunicaci√≥n con API REST
- **PDF Generation** - Generaci√≥n de reportes en PDF
- **Share Plus** - Compartir archivos y reportes

### Backend (API REST)
- **Python 3.8+** - Lenguaje del servidor
- **FastAPI** - Framework web moderno y r√°pido
- **MongoDB** - Base de datos NoSQL
- **PyMongo** - Driver de MongoDB para Python
- **Pydantic** - Validaci√≥n de datos
- **JWT** - Autenticaci√≥n por tokens
- **Uvicorn** - Servidor ASGI
- **Passlib + Bcrypt** - Encriptaci√≥n de contrase√±as

## Ì†ΩÌ≥ã Requisitos del Sistema

### Para el Frontend (Flutter)
- Flutter SDK ‚â• 3.7.2
- Dart SDK ‚â• 3.7.2
- Android Studio / VS Code
- Dispositivo Android 5.0+ (API 21+) o iOS 11.0+

### Para el Backend (Python)
- Python 3.8+
- MongoDB 4.4+
- Pip (gestor de paquetes)

## Ì†ΩÌª†Ô∏è Instalaci√≥n y Configuraci√≥n

### 1. Clonar el Repositorio
```bash
git clone https://github.com/tu-usuario/riocaja-smart.git
cd riocaja-smart
```

### 2. Configuraci√≥n del Backend

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
# Crear archivo .env en la ra√≠z del proyecto
MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net/riocaja_smart
DATABASE_NAME=riocaja_smart
SECRET_KEY=tu-clave-super-secreta
```

#### Iniciar el Servidor
```bash
# OPCI√ìN A: Comando simple
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# OPCI√ìN B: Con screen (recomendado para producci√≥n)
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

### 3. Configuraci√≥n del Frontend

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

#### Ejecutar la Aplicaci√≥n
```bash
# Limpiar cache
flutter clean
flutter pub get

# Ejecutar en modo debug
flutter run

# Generar APK para Android
flutter build apk --release
```

## Ì†ºÌæØ Uso del Sistema

### Roles de Usuario

#### Ì†ΩÌ±®‚ÄçÌ†ΩÌ≤º Administrador
- Aprobar/rechazar nuevos usuarios
- Asignar c√≥digos de corresponsal
- Gestionar roles de usuarios
- Crear y administrar mensajes del sistema
- Acceso completo a todos los comprobantes y reportes

#### Ì†ΩÌ¥ß Operador
- Crear mensajes del sistema
- Ver usuarios pendientes
- Acceso a reportes y comprobantes (limitado)

#### Ì†ΩÌ≥ñ Lector (Corresponsal)
- Escanear y gestionar comprobantes
- Generar reportes de cierre diarios
- Ver mensajes del sistema
- Acceso solo a sus propios comprobantes

### Flujo de Trabajo T√≠pico

1. **Registro**: El corresponsal se registra en la app
2. **Aprobaci√≥n**: Un administrador aprueba la cuenta y asigna c√≥digo
3. **Completar Perfil**: El usuario completa su perfil con informaci√≥n del local
4. **Escaneo**: Captura comprobantes con la c√°mara
5. **Verificaci√≥n**: Revisa y confirma los datos extra√≠dos por OCR
6. **Gesti√≥n**: Consulta historial y filtra transacciones
7. **Reportes**: Genera reportes de cierre al final del d√≠a

## Ì†ΩÌ≥ä Endpoints de la API

### Autenticaci√≥n
- `POST /api/v1/auth/register` - Registro de usuarios
- `POST /api/v1/auth/login` - Inicio de sesi√≥n
- `GET /api/v1/auth/me` - Informaci√≥n del usuario actual
- `POST /api/v1/auth/complete-profile` - Completar perfil

### Administraci√≥n
- `GET /api/v1/auth/pending-users` - Usuarios pendientes
- `POST /api/v1/auth/approve-user-with-code` - Aprobar usuario con c√≥digo
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
- `POST /api/v1/messages/mark-read` - Marcar como le√≠do

## Ì†ΩÌ¥ß Comandos de Gesti√≥n del Servidor

### Iniciar con Screen
```bash
# Crear nueva sesi√≥n
screen -S riocaja_server

# Dentro de la sesi√≥n
cd /ruta/a/tu/proyecto
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Gestionar Sesiones Screen
```bash
# Ver sesiones activas
screen -ls

# Conectar a sesi√≥n existente
screen -r riocaja_server

# Salir sin cerrar (desde dentro): Ctrl+A, luego D

# Detener sesi√≥n completamente
screen -S riocaja_server -X quit
```

### Verificaci√≥n del Sistema
```bash
# Verificar que el servidor responde
curl http://34.63.192.239:8080/

# Ver documentaci√≥n de la API
curl http://34.63.192.239:8080/docs

# Verificar puerto en uso
netstat -tlnp | grep :8080
```

## Ì†ΩÌ∞õ Soluci√≥n de Problemas

### Problemas Comunes

#### Error de Conexi√≥n en la App
1. Verificar que el servidor est√© ejecut√°ndose: `curl http://34.63.192.239:8080/`
2. Comprobar la IP en los archivos de configuraci√≥n de Flutter
3. Verificar conectividad de red del dispositivo

#### Error de Autenticaci√≥n
1. Verificar que la base de datos MongoDB est√© disponible
2. Comprobar las variables de entorno (.env)
3. Verificar que el token JWT no haya expirado

#### Problemas con OCR
1. Asegurar buena iluminaci√≥n al capturar
2. Mantener el comprobante dentro del marco
3. Verificar que Google ML Kit est√© correctamente instalado

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

## Ì†æÌ¥ù Contribuci√≥n

### Estructura del Proyecto
```
riocaja-smart/
‚îú‚îÄ‚îÄ app/                    # Backend (Python/FastAPI)
‚îÇ   ‚îú‚îÄ‚îÄ models/            # Modelos de datos
‚îÇ   ‚îú‚îÄ‚îÄ routes/            # Rutas de la API
‚îÇ   ‚îú‚îÄ‚îÄ services/          # L√≥gica de negocio
‚îÇ   ‚îî‚îÄ‚îÄ main.py            # Punto de entrada
‚îú‚îÄ‚îÄ lib/                   # Frontend (Flutter)
‚îÇ   ‚îú‚îÄ‚îÄ models/            # Modelos de datos
‚îÇ   ‚îú‚îÄ‚îÄ providers/         # Gesti√≥n de estado
‚îÇ   ‚îú‚îÄ‚îÄ screens/           # Pantallas de la app
‚îÇ   ‚îú‚îÄ‚îÄ services/          # Servicios de API
‚îÇ   ‚îî‚îÄ‚îÄ widgets/           # Componentes reutilizables
‚îú‚îÄ‚îÄ requirements.txt       # Dependencias Python
‚îú‚îÄ‚îÄ pubspec.yaml          # Dependencias Flutter
‚îî‚îÄ‚îÄ README.md             # Este archivo
```

### C√≥mo Contribuir
1. Fork el repositorio
2. Crear una rama para la nueva funcionalidad
3. Hacer commits con mensajes descriptivos
4. Enviar Pull Request con descripci√≥n detallada

## Ì†ΩÌ≥Ñ Licencia

Este proyecto est√° licenciado bajo los t√©rminos de la [Licencia MIT](LICENSE).

## Ì†ºÌ∂ò Soporte

Para reportar bugs o solicitar nuevas funcionalidades, por favor crear un issue en el repositorio de GitHub.

### Informaci√≥n de Contacto
- **Proyecto**: R√≠oCaja Smart
- **Banco**: Banco del Barrio - Banco Guayaquil
- **Versi√≥n**: 1.0.0

---

**Nota**: Este sistema est√° dise√±ado espec√≠ficamente para corresponsales bancarios del Banco del Barrio. Para uso en producci√≥n, asegurar configuraciones de seguridad apropiadas y certificados SSL v√°lidos.