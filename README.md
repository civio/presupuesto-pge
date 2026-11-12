# presupuesto-pge

Tema de ¿Dónde van mis impuestos? para los Presupuestos Generales del Estado.

### Los datos

Los ficheros de `data/es/pais/<año>/` (gastos, ingresos y las tres clasificaciones, que cambian cada año) son una copia de la carpeta `output/<año>/` de [scraper-pge](https://github.com/civio/scraper-pge), antes llamado `pge-parser`, que los extrae de los ficheros que publica el Ministerio de Hacienda. Si falta o sobra algo, se corrige en el _scraper_ (sus `corrections/`) y se vuelve a copiar, para que sigan coincidiendo.

Las excepciones son 2019 y 2020, que no tuvieron presupuestos aprobados: se prorrogó el de 2018, así que sus carpetas son una copia de la de 2018 con el año cambiado.

Los programas que se renombraron en 2023 se traducen a sus códigos anteriores al cargarlos, para no romper la serie histórica (ver `PROGRAMME_MAPPING_2023` en el cargador).
