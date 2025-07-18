# Quiet Stream

Esta es una aplicación de Interfaz de Usuario de Terminal (TUI) diseñada para ayudar a gestionar y reproducir tus streams y videos favoritos. Construida con Textual, SQLModel, SQLite y python-vlc, ofrece una forma sencilla y potente de interactuar con tu contenido multimedia directamente desde tu terminal.

## Funciones principales : 

- Gestión de streams y videos: Agrega, edita y elimina tus entradas de streams y videos.

- Reproducción integrada: Reproduce streams de audio y videos de plataformas como YouTube directamente en la terminal.

- Control de Reproducción: Controles para reproducir, pausar, detener, avanzar y retroceder entre tus contenidos.

- Categorización flexible: Organiza tu contenido asignándole una o varias categorías.

- Interfaz de Usuario Intuitiva: Navega y gestiona tu contenido con una interfaz limpia y amigable basada en Textual.

- Persistencia de Datos: Tus datos se guardan de forma segura en una base de datos SQLite local.

## Capturas de pantalla

A continuación, se muestran algunas imágenes del programa en funcionamiento:

![screenshot](https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhxaMq4llntag73k0AKVQUOHdgi9nMJCpQuezSgJghyEcbikYuccz0m6a2o5eF-qu22rO5q6FrdDpGaYXDsW8QfFzxyQg5q56sfCMnAYadlLej7fOraOEuC8mKkS4WD3HH5n4RUPdtc11koC1iTUq0A0WsL0A4-408k5v7Bgxch9lO3iXm4pVipg_ZJ3UQ/s1112/1.png)

![screenshot](https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhs5Y4aqwUYdckCo5xdh630GlFsQYjtnDvMdhvavupbcnGndn_yKgU1zp_ITdvy88RIIAvpjE9Y-OZlrSqUnK-ZKgmwX2US8pmOYFJdk3Z-9zctKjsqp0KqeFmkO5tDg4rO9HFLwkQ1Y6DyvE-BmVNOHA3I3UWFLPGdgHOeWm04OgP11FpNti4_yorVmh8/s1110/2.png)

![screenshot](https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgcBUmvHaKalrqnlhLuFfozBht9TVe6_yc-O9XdIk1BXJNvBS8PfwSiWNvF63qhKnsy4sYpQ2PqTqHtEjS75ynWJJdpHsJIopfDrqaYLooZ18AIRhA3pNXnVtzI7TSB16eAo5hyWf_f_09U7a8oPXoQ0sEFPw42TQT17E1Izlv5iWyOITLS9XdjFLbpvaE/s1110/3.png)

## Instalación

Se necesitan seguir estos pasos para poner en marcha Quiet Stream en tu sistema:

1. Requisitos Previos:

* **Python 3.8+**
* **VLC Media Player:** Necesitas tener VLC instalado en tu sistema, ya que `python-vlc` actúa como una interfaz para él. Puedes descargarlo directamente desde [videolan.org](https://www.videolan.org/vlc/).

2. Clona el repositorio:

```
git clone https://github.com/IsmaelHeredia/quiet-stream-python.git
```

```
cd quiet-stream-python
```

3. Instala las dependencias:

```
pip install -r requirements.txt
```

4. Inicializa la base de datos:

El archivo streams.db y las tablas necesarias se crearán automáticamente la primera vez que inicies la aplicación.

5. Ejecución:

Para iniciar la aplicación, ejecuta el siguiente comando en tu terminal:

```
python main.py
```