# Quiet Stream

Aplicación TUI (Terminal User Interface) para gestionar y reproducir streams de audio y videos, construida con Textual, SQLModel, SQLite, python-vlc, yt-dlp y httpx.

## Funciones principales

- **Gestión de streams y videos:** agregar, editar y eliminar entradas.
- **Reproducción integrada:** streams de audio (URL directa) y videos (YouTube y similares vía yt-dlp).
- **Controles de reproducción:** anterior, siguiente, detener y volumen.
- **Búsqueda y filtros:** por nombre y por categoría.
- **Importar / exportar JSON:** backup y carga de listas, con omisión automática de duplicados por nombre o link.
- **Validación de enlaces:** comprueba si los streams responden; permite detener el proceso, seleccionar cuáles eliminar y confirmar.
- **Temas Gruvbox Light / Dark:** se alternan con `Ctrl+T` y la preferencia se guarda entre sesiones.
- **Interfaz responsive:** tablas y menú se adaptan al tamaño de la terminal.
- **Persistencia local:** los datos se guardan en SQLite (`streams.db`).

## Capturas de pantalla

![screenshot](https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhPFY7MSTCl-KopzEj2gOkpwuYLDuiAXIsuKEoi-6cloZ2VN2OmBQYv_E2dHfvXN7Z7ITOUY7wwLQz0Poi73-ddpn4MnKdJnnUh_UL_F1T8c5u-UgKaR8LKHDhTvyAD0ThiQUY_R3QgqYQOfzoMnQqFVOAXXYA7hyphenhyphenPwbL3Mj6hp0rpeceQQlJ_zNkmM_Zw/s1148/1.png)

![screenshot](https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjOg8Jx-DVtQHIgNlV9FD2PkyRKR7yFMVS42ypP5_QViF53Vly7MRvIDbcp9t2gA3i1z70YUF2OziHo20NYXvZebbUomikx188m9s4cdybJAIgK9VIz2ytMXjNMg6vAX1VGN0xNB96yNYzSqBDLc6J31O9j0yYbiSxxIZGtmaJhsFLc_Wu8rm1MbwIkK5Y/s1147/2.png)

![screenshot](https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiysszR-maurY4A4KGsO2CcD3K02LTYaaaIkdfZ-0KvWDA6TOvlkedrTtiZWhyWflHmYg13fQgTAws4kvJfpiJT4cX_KpMf9BVTWsskhyphenhyphenEuR2_XX2JKsvXKC5NP2BIzcFLB-5ly3VMKkFkl-SChLZenTD1WuM9HUXEZU0sbXBlaN7E_uCL88GnQRdzd0D8/s1146/3.png)

![screenshot](https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhnOj9Scz-KW5iaNpl0UZmDMV9H_Pi7WI9J6gZ_Vj0H3H4ddMn1rReAqDJ5hgkIeNy2vgGY9Ts5P0uSLAxiH1p5YxlnlNueptkYV5Wn-BfjzEm-XS18iq0lsnhAbsni9LoKoW9Zgukgh4DmZuGzBuexQ7IUIYf8aOLFu2YcqY_3k5kdgbOvhX2eShZ5_6E/s1145/4.png)

![screenshot](https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjb1HZsKt9WffFz4rfl2i5SayQO36ELQs8v2zz82KqttOZlC18xIowCXDoLgpEli9bLLHt9ijFRbuOG78iByfJEc7xZsHtQav93crlsUAFJUcqOfL5_sh2ogXCPuXWVYYA5_Wlfs6xi355nWAPFqdLkg7lO1AnbPgGX_KdeMR_vk50YD6UaNbqC-BnCmTU/s1143/5.png)

![screenshot](https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEg8r8QYBtEqT_JAQiwM8P7qiki2rxjogRl06kRBiadGc4sBEXyqrhrZlmOT5OmieuwrFMvS5ygvrK7Z0sx8yNfoVnJR6F_wYjyX2E5J3c15-7bxjjVGk2YszrokNeL8A0bJRorqcYlUymxtf7cAXMWg-G2RK4SZvmg5fRkkAyWINtlug3aoZKxOmHj5i_8/s1139/6.png)

## Requisitos

- **Python 3.8+**
- **VLC Media Player** instalado en el sistema ([videolan.org](https://www.videolan.org/vlc/))

## Instalación

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/IsmaelHeredia/quiet-stream-python.git
   cd quiet-stream-python
   ```

2. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Ejecutar:

   ```bash
   python main.py
   ```

## Importación y exportación (Formato JSON)

Los respaldos exportados utilizan una lista con la siguiente estructura por cada elemento, la cual también se requiere para importar datos:

```json
[
  {
    "nombre": "Mi stream",
    "link": "https://ejemplo.com/stream.mp3",
    "categorias": "rock, radio",
    "tipo": "stream"
  },
  {
    "nombre": "Video de ejemplo",
    "link": "https://www.youtube.com/watch?v=...",
    "categorias": "musica",
    "tipo": "video"
  }
]
```