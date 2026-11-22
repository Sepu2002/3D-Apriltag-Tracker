### **1. Introducción: ¿Qué son los Marcadores Fiduciales?**
En visión computacional, un "marcador fiducial" es un objeto colocado en el campo de visión que actúa como punto de referencia conocido. A diferencia del reconocimiento de objetos naturales (como detectar una taza o un gato), los marcadores están **diseñados artificialmente** para ser fáciles de detectar y decodificar, incluso en condiciones difíciles (baja resolución, desenfoque de movimiento, iluminación extrema).



**Diferencia clave con códigos QR:**
* **QR Code:** Optimizado para almacenar *datos* (URLs, texto). Son complejos y difíciles de detectar a distancia o con ángulos agudos.
* **AprilTags (y ArUco):** Optimizados para la **geometría**. Tienen poca data (solo un ID numérico) pero bordes muy definidos que permiten calcular su orientación precisa en el espacio 3D.

**¿Por qué usamos la familia `36h11`?**
El nombre significa que es una cuadrícula de **36 bits** con una distancia de Hamming de **11**.
* **Hamming Distance 11:** Significa que el sistema puede detectar y corregir hasta varios bits erróneos. Si hay un reflejo en el tag, el algoritmo matemático "reconstruye" el bit faltante.

---

### **2. El Pipeline de Visión (Algoritmos de Detección 2D)**
Antes de llegar al 3D, el sistema debe procesar la imagen cruda (matriz de píxeles). Esto no es una simple búsqueda de patrones; es un pipeline secuencial:

1.  **Adquisición y Conversión:**
    * La cámara entrega una imagen en espacio de color BGR.
    * Se convierte a **Escala de Grises** (intensidad luminosa $Y = 0.299R + 0.587G + 0.114B$). La información de color es irrelevante para la geometría y añade ruido computacional.

2.  **Segmentación (Adaptive Thresholding):**
    * En lugar de usar un umbral fijo (ej. "todo lo menor a 127 es negro"), usamos **Umbralización Adaptativa**.
    * El algoritmo analiza ventanas locales de píxeles (vecindarios). Esto permite detectar el tag incluso si una mitad está bajo una sombra fuerte y la otra bajo luz directa.

3.  **Extracción de Contornos y Filtrado de Cuadriláteros:**
    * Se utiliza un algoritmo de componentes conectados (como *Union-Find*) para agrupar píxeles oscuros.
    * Se ajustan líneas a los bordes de estos "blobs".
    * **Criterio de Rechazo:** Si el blob no tiene 4 esquinas o sus bordes no son convexos, se descarta.

4.  **Homografía y Decodificación:**
    * En la imagen, el tag se ve deformado por la perspectiva (trapezoide).
    * El sistema calcula una **Matriz de Homografía ($H$)** que mapea los píxeles del trapezoide a un cuadrado perfecto canónico en memoria.
    * Sobre este cuadrado "virtual", se leen los bits (blanco/negro) y se verifica el ID contra el diccionario `36h11`.

---

### **3. Del 2D al 3D: El Problema PnP (Perspective-n-Point)**
Esta es la parte central de la asignatura de percepción. ¿Cómo pasamos de píxeles $(u, v)$ a metros $(X, Y, Z)$?

Utilizamos el **Modelo de Cámara Pinhole (Estenopeica)**. La relación fundamental es:

$$s \begin{bmatrix} u \\ v \\ 1 \end{bmatrix} = \mathbf{K} \cdot [\mathbf{R} | \mathbf{t}] \cdot \begin{bmatrix} X_{world} \\ Y_{world} \\ Z_{world} \\ 1 \end{bmatrix}$$

Donde:
* **$(u, v)$:** Puntos detectados en la imagen (Fase anterior).
* **$(X, Y, Z)_{world}$:** Puntos físicos reales. Aquí es donde definimos `TAG_SIZE`. Le decimos al sistema: *"Sabemos que en la realidad, las esquinas están a 5cm de distancia"*.
* **$\mathbf{K}$ (Matriz Intrínseca):** Define las propiedades internas de la cámara (Distancia focal y centro óptico). En el código la aproximamos basándonos en la resolución.
* **$[\mathbf{R} | \mathbf{t}]$ (Matriz Extrínseca):** La incógnita que queremos resolver.
    * **$\mathbf{R}$ (Rotación):** Orientación del tag.
    * **$\mathbf{t}$ (Traslación):** Posición del tag.

**El Algoritmo de Solución (Levenberg-Marquardt):**
La función `cv2.solvePnP` no "despeja" la ecuación simplemente. Utiliza un método iterativo de optimización no lineal:
1.  Estima una posición inicial del tag.
2.  Proyecta matemáticamente dónde caerían los puntos 2D con esa estimación.
3.  Calcula el **Error de Reproyección** (distancia entre el píxel real detectado y el píxel proyectado).
4.  Ajusta $\mathbf{R}$ y $\mathbf{t}$ para minimizar ese error (Descenso de Gradiente).

---

### **4. Mapeo y Persistencia de Estado**
Más allá de la visión instantánea, el sistema implementa conceptos de **Robótica Móvil**:

* **Transformación de Coordenadas:**
    El sistema convierte coordenadas del *Frame de la Cámara* (donde Z es profundidad) al *Frame del Mapa* (donde convertimos ejes para visualización en Matplotlib).
* **Odometría Visual (Trajectory Tracking):**
    Mediante el uso de estructuras de datos tipo cola (`deque`), el sistema almacena el historial de vectores de estado $\vec{x}_t, \vec{x}_{t-1}, ... \vec{x}_{t-n}$. Esto permite visualizar no solo la *pose* actual, sino la *cinemática* (el movimiento) del objeto en el tiempo.

### **Resumen para la presentación:**
> "Este sistema no es una simple detección de imágenes; es un sistema de **medición fotogramétrica**. Convierte información 2D ambigua en datos espaciales 3D precisos resolviendo la geometría proyectiva de la escena, permitiendo tanto Realidad Aumentada (proyección hacia adelante) como Mapeo Espacial (reconstrucción de la escena)."