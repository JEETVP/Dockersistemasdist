# Ejercicio práctico de incorporación de Docker con Redis para registro de usuarios  
**Autor:** Roberto Villegas Ojeda  

---

## Objetivo del programa
Poder añadir usuarios, validando que no estén previamente registrados, y guardar las visitas a cada endpoint con Redis.

---

## Estructura básica
Primero cargamos las dependencias necesarias, la URL de la base de datos y el host de Redis. Adicionalmente añadimos validaciones tipo **regex** para:

- **Correo electrónico:** permitir solo dominios `@hotmail.com`, `@outlook.com` y `@gmail.com`.
- **Contraseña:** permitir que solo se añada si tiene **una mayúscula, una minúscula y un número**, con longitud de **1 a 50 caracteres**.

---

## Validaciones (funciones y arranque)
Primero, tenemos que asegurar que haya conexión a Redis, a la base de datos y que exista la tabla de usuarios.

- `get_redis()`: crea la conexión hacia Redis.
- `incr_visits()`: por cada visita a ciertos endpoints, llama a Redis y suma 1 al contador de visitas.

También tenemos que esperar la conexión con PostgreSQL haciendo 20 intentos con un `try/except`:

- `wait_for_db()`: intenta conectar hasta 20 veces; si falla, devuelve error.

En caso de que no exista aún la tabla, la crea para poder tener persistencia de usuarios:

- `ensure_users_table()`: hace la conexión a la base de datos y manda el comando `CREATE TABLE` para crear `users` si no existe.

---

## Endpoints

### `/` (GET)
Muestra un mensaje de bienvenida con la descripción de los endpoints.  
Se puede acceder directamente desde el navegador. Para pruebas de `POST` y `GET` se puede usar Postman.

### `/health` (GET)
Hace conexión con Redis y verifica que tenga respuesta, y también devuelve la hora del servidor (consultada desde PostgreSQL).

### `/visits` (GET)
Muestra el contador de cuántas visitas han tenido los endpoints, usando Redis (contador incrementado por la lógica de visitas).

### `/users` (POST)
Primero agrega una visita llamando a la función `incr_visits()` y solicita los datos:

- `nombre`
- `apellido`
- `email`
- `password`

Luego hace las validaciones:
- que reciba todos los datos
- que el `email` cumpla el regex permitido
- que la `password` cumpla el regex (mayúscula, minúscula, número y 1 a 50 caracteres)

Si no cumple, manda un error **400 (Bad Request)** y no permite hacer la adición en la BD.  
En caso de que sí pueda, manda el mensaje de que pudo crear el usuario y devuelve el `id` con el que está registrado y un **200 OK**.

### `/users` (GET)
Primero igual se añade al contador de visitas, y hace la conexión a la base de datos para traer de la tabla `users`, en el orden en el que fueron creados, todos los usuarios.

---

## Compilación / Ejecución (qué pasa cuando se corre)
Al correr el código, lo primero que va a hacer es:

1. **Esperar conexión a la base de datos** (`wait_for_db()`).
2. **Verificar que exista la tabla de usuarios** y crearla si no existe (`ensure_users_table()`).
3. Iniciar la aplicación Flask para servir los endpoints.

Esto permite que el sistema funcione bien desde el primer arranque, asegurando persistencia en SQL y el contador de visitas con Redis.