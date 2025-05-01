# RíoCaja Smart API

Backend API para la aplicación RíoCaja Smart, desarrollado con FastAPI y MongoDB.

## Descripción

RíoCaja Smart API es un backend que permite gestionar comprobantes de transacciones bancarias, consultar reportes y proveer datos a la aplicación móvil RíoCaja Smart.

## Requisitos previos

- Python 3.7 o superior
- Pip (gestor de paquetes de Python)
- Cuenta de MongoDB Atlas (o MongoDB local)
- Git (opcional, para clonar el repositorio)

## Instalación

### 1. Clonar el repositorio (o descargar)

```bash
git clone https://github.com/tu-usuario/riocaja-smart-api.git
cd riocaja-smart-api
```

### 2. Crear un entorno virtual (recomendado)

En Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

En macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:

```
MONGO_URI=tu_cadena_de_conexion_de_mongodb
DATABASE_NAME=tu_nombre_de_base_de_datos
```

Reemplaza `tu_cadena_de_conexion_de_mongodb` y `tu_nombre_de_base_de_datos` con tus propias credenciales de MongoDB.

> **IMPORTANTE**: Nunca subas el archivo `.env` con tus credenciales reales a un repositorio público.

## Ejecución

### Iniciar el servidor de desarrollo

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

El servidor se iniciará en `http://localhost:8000`

### Acceder a la documentación de la API

Una vez que el servidor esté en ejecución, puedes acceder a la documentación interactiva de la API en:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Estructura del proyecto

```
riocaja-smart-api/
├── app/
│   ├── __init__.py
│   ├── config.py       # Configuración de la aplicación
│   ├── main.py         # Punto de entrada principal
│   ├── models/         # Modelos de datos (Pydantic)
│   ├── routes/         # Rutas de la API
│   └── services/       # Servicios para lógica de negocio
├── .env                # Variables de entorno (no incluir en git)
└── requirements.txt    # Dependencias del proyecto
```

## Endpoints de la API

La API proporciona los siguientes endpoints:

- `GET /api/v1/receipts/`: Obtener todos los comprobantes
- `GET /api/v1/receipts/date/{date}`: Obtener comprobantes por fecha (formato: DD/MM/YYYY)
- `POST /api/v1/receipts/`: Crear un nuevo comprobante
- `GET /api/v1/receipts/report/{date}`: Generar reporte de cierre para una fecha específica
- `DELETE /api/v1/receipts/{transaction_number}`: Eliminar un comprobante por número de transacción

## Ejemplo de uso

### Crear un nuevo comprobante

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/receipts/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "banco": "Pichincha",
  "fecha": "29/04/2025",
  "hora": "15:30",
  "tipo": "Depósito",
  "nro_transaccion": "123456789",
  "nro_control": "987654321",
  "local": "Agencia Principal",
  "fecha_alternativa": "",
  "corresponsal": "Banco XYZ",
  "tipo_cuenta": "Ahorros",
  "valor_total": 100.50,
  "full_text": "Texto completo del comprobante"
}'
```

## Notas de seguridad

1. **Proteger credenciales**: Nunca incluyas credenciales reales en archivos que suban a repositorios públicos.
2. **En producción**: Configura correctamente CORS en `app/main.py` para permitir solo las orígenes necesarios.
3. **Seguridad adicional**: En un entorno de producción, considera implementar autenticación y autorización.

## Solución de problemas

### Problemas de conexión con MongoDB

Si tienes problemas para conectarte a MongoDB, asegúrate de:

1. Verificar que tu string de conexión sea correcta
2. Confirmar que tu IP esté en la lista blanca de MongoDB Atlas
3. Revisar los logs para identificar el problema específico

### Error "ModuleNotFoundError"

Si ves este error, asegúrate de que:
1. El entorno virtual esté activado
2. Todas las dependencias estén instaladas correctamente
3. Estés ejecutando el servidor desde la raíz del proyecto

## Contribuir

Si deseas contribuir a este proyecto, por favor:

1. Haz un fork del repositorio
2. Crea una rama para tu función (`git checkout -b feature/nueva-funcion`)
3. Haz commit de tus cambios (`git commit -m 'Agrega nueva función'`)
4. Haz push a la rama (`git push origin feature/nueva-funcion`)
5. Abre un Pull Request

## Licencia

[Incluir información de licencia aquí]
