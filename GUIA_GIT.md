# 🚀 Guía de Git y GitHub para el Bot de Binance

Git es el estándar de la industria para el control de versiones. Te permite guardar "fotos" (commits) de tu código para volver atrás si algo falla y trabajar de forma segura.

## 1. Conceptos Fundamentales

- **Repositorio (Repo):** La carpeta del proyecto que Git está vigilando.
- **Commit:** Una "captura" de tus cambios. Cada commit tiene un mensaje descriptivo.
- **Rama (Branch):** Una línea de tiempo. La principal suele ser `main`.
- **Remote:** Una copia de tu repo en internet (como GitHub).
- **Push:** Enviar tus commits locales al servidor (GitHub).
- **Pull:** Traer los cambios del servidor a tu computadora.

## 2. Comandos Esenciales (Tu día a día)

| Comando                       | Acción                                                 |
| :---------------------------- | :----------------------------------------------------- |
| `git status`                  | Mira qué archivos han cambiado.                        |
| `git add .`                   | Prepara todos los archivos para el siguiente guardado. |
| `git commit -m "Explicación"` | Guarda la foto con un mensaje descriptivo.             |
| `git push origin main`        | Sube tus cambios a la nube (GitHub).                   |
| `git log`                     | Mira el historial de versiones.                        |

## 3. Seguridad de Datos (CRÍTICO) 🛡️

Nunca, jamás, subas tus llaves API o archivos `.env` a GitHub. Para evitar esto, usamos un archivo llamado `.gitignore`. 
He configurado este archivo para que ignore automáticamente:
- Tus credenciales de Binance (`.env`).
- Bases de datos locales (`.db`).
- Carpeta de librerías (`node_modules`, `.venv`).

## 4. Cómo Actualizar tu GitHub (Flujo de trabajo)

Cuando termines una nueva mejora:
1. `git add .`
2. `git commit -m "Añadida nueva estrategia de trading"`
3. `git push origin main`

---

> [!TIP]
> **Versión 1.7:** He etiquetado este estado actual como la versión 1.7 oficial del bot. ¡Felicidades por llegar hasta aquí!
