---
name: mle-workflow
description: Disciplina para proyectos de machine learning — contrato de datos, baseline, validación antes de dar por buena una versión, análisis de errores y trazabilidad — adaptada a cuatro perfiles (estudio + informe, modelo que se re-ejecuta, modelo en producción, entregable europeo). Úsala al empezar o cambiar un modelo, preparar datos de entrenamiento, comparar versiones, o antes de cerrar un informe o entregable con cifras de un modelo.
---

# Flujo de trabajo de ML

Esta skill no dice cómo organizar carpetas (eso es `ml-pipeline-workflow`), sino cómo trabajar
para que las cifras de un modelo sean fiables: saber qué se predice y para qué, comprobar los
datos antes de entrenar, comparar siempre con algo sencillo, revisar los errores y dejar rastro
de cada decisión. La idea de fondo: un modelo solo vale lo que valen las comprobaciones que lo
respaldan. Aplica solo lo que pida el perfil del proyecto; no metas maquinaria que nadie va a usar.

## Primero: qué perfil tiene el proyecto

Antes de tocar código, pregunta (o deduce y dilo en voz alta) qué tipo de proyecto es. Pistas:

- ¿El resultado final es un documento que se entrega una vez? → Estudio + informe.
- ¿El mismo código se vuelve a lanzar cuando llegan datos nuevos? → Re-ejecutable.
- ¿Otro sistema llama al modelo sin que una persona mire cada resultado? → Producción.
- ¿Las cifras acaban en un entregable de un proyecto europeo? → Entregable europeo.

Estudio → Re-ejecutable → Producción son acumulativos: cada uno incluye lo imprescindible del
anterior. Entregable europeo se suma al perfil de origen. Un proyecto puede combinar perfiles:
un modelo de la climatización de un edificio de oficinas es re-ejecutable (entran meses nuevos de datos) y además alimenta un entregable europeo, así que se suman los requisitos de ambos.

### Perfil: Estudio + informe

Ejemplo (inventado): un estudio de ahorro en una fábrica de muebles. Se estudia si sustituir un compresor de aire comprimido antiguo por uno de velocidad variable ahorra lo bastante para optar a una ayuda de eficiencia energética. Se trabaja con los Excel de consumos y producción de la fábrica, el modelo pasa por versiones (V1 en `obsoleto/`, V2 con un ahorro aparente, V3 vigente en «modelo V3») y el resultado es un informe. Conclusión actual (V3, de la memoria de trazabilidad del proyecto): con estos datos el ahorro no se puede afirmar; la sustitución explica unos 50.000 kWh/año, pero el intervalo al 90 % va de −30.000 a 130.000 kWh/año e incluye el cero. Los 150.000 kWh/año de la V2 eran una sola cifra sin intervalo y quedan superados.

Imprescindible:
- Una pregunta clara y escrita (ver «Contrato de predicción»).
- Datos validados: fechas bien leídas, unidades revisadas, huecos y duplicados identificados.
- Un baseline con el que comparar (ver «Baseline primero»).
- Análisis de errores: dónde falla el modelo y por qué.
- Trazabilidad de cada cifra del informe: de qué fichero, qué versión del modelo y qué script
  sale cada número. Esto vive en la memoria de trazabilidad del proyecto.

No hace falta:
- API (interfaz por la que otro programa pide una predicción, por ejemplo una URL que la
  devuelve), Docker (empaquetar la aplicación en un contenedor: un entorno con todo lo necesario
  para que funcione igual en cualquier máquina), despliegue gradual (canary: activar la versión
  nueva para una parte pequeña del uso antes que para todo) ni monitorización: nadie va a llamar
  al modelo.
- Pipeline (la cadena de pasos, de los datos crudos a la predicción o el informe, que se ejecuta
  en orden) automatizado de reentrenamiento.
- Herramientas pesadas de seguimiento de experimentos si basta una tabla de versiones en la memoria.

### Perfil: Re-ejecutable

Ejemplo (inventado): un modelo de la climatización de un edificio de oficinas. Un pipeline que pronostica, cada tarde y hora a hora, el consumo eléctrico de la climatización del día siguiente. Se vuelve a lanzar cuando llegan datos nuevos y la salida es un Excel.

Imprescindible:
- Todo lo del perfil Estudio + informe.
- Pipeline repetible: se lanza con un solo comando, sin pasos manuales en un notebook (cuaderno
  interactivo de código y resultados, tipo Jupyter, cómodo para explorar pero que no se
  reejecuta solo).
- Idempotencia: lanzar dos veces la misma fase con los mismos datos da el mismo resultado y no
  duplica filas ni pisa resultados buenos. Ejemplo: si al relanzar la carga de un mes se añade
  otra vez ese mes al histórico, el pipeline no es idempotente.
- Comprobación de deriva: antes de predecir, mirar si los datos nuevos se parecen a los de
  entrenamiento. Deriva es que cambien con el tiempo (otra estación del año, un sensor
  recalibrado, una sala que pasa a otro uso). Si cambian mucho, la predicción deja de ser
  fiable aunque el código funcione.

No hace falta:
- API ni contenedores, salvo que otro sistema consuma el Excel automáticamente.
- Despliegue gradual ni pruebas A/B (comparar dos versiones repartiendo el tráfico real entre
  ellas para medir cuál funciona mejor).

### Perfil: Producción

Ejemplo (inventado): un servicio en Docker que toma las previsiones del modelo de climatización y las publica cada tarde en la base de datos del sistema de gestión del edificio, que las usa para programar el arranque de los equipos sin que nadie las revise una a una.

Imprescindible:
- Todo lo del perfil Re-ejecutable.
- Contrato de entrada y salida: qué columnas, tipos, unidades, zona horaria y rangos se esperan,
  y qué se hace si llega algo inválido (rechazarlo con un error claro, no inventar).
- Versión de modelo identificable: cada respuesta o fichero de salida dice qué versión la produjo.
- Vuelta atrás: poder volver a la versión anterior sin reentrenar, cambiando solo qué artefacto
  (el fichero del modelo entrenado, con su preprocesado y configuración) se carga.
- Monitorización: además de «la API responde», vigilar la calidad de los datos que entran y la
  distribución de las predicciones que salen.

No hace falta:
- Infraestructura de gran escala (almacenes centralizados de variables, réplicas que reciben el
  tráfico real sin afectar a nadie para probar, paneles por cohorte: grupo de usuarios o casos con
  un rasgo común, seguido a lo largo del tiempo) si el volumen y el número de usuarios no lo
  justifican. Basta con registros y una comprobación periódica.

### Perfil: Entregable europeo

Ejemplo (inventado): una entrega a un programa europeo que usa resultados del modelo de climatización de oficinas: la misma cifra (p. ej. un ahorro o una métrica del modelo) tiene que coincidir en el texto del entregable y en su anexo Excel.

Imprescindible:
- Todo lo del perfil de origen (normalmente Re-ejecutable o Estudio).
- Coherencia dentro y entre entregables: la misma cifra que aparece en el anexo Excel y en el
  texto coincide exactamente (mismo valor, unidad y redondeo), y no contradice a entregables
  anteriores sin explicarlo.
- Cifras citables: cada número del entregable se puede rehacer a partir de una versión concreta
  de datos y modelo, con fecha de corte.

No hace falta:
- Cambiar el modelo para el entregable: se cita la versión validada, no se reentrena a última hora.

## Contrato de predicción

Antes de escribir código de modelo, escribe en pocas líneas (en el plan, el journal o la memoria):

```text
Qué se predice:
Para quién y qué decisión cambia:
Métrica principal (acordada con el usuario):
Error inaceptable:
Error aceptable:
Datos y fecha de corte:
Baseline:
Supuestos, limitaciones y lo que no se sabe:
Siguiente experimento:
```

El punto clave es empezar por la decisión, no por el modelo. En el estudio del compresor la decisión es si el ahorro atribuible a la sustitución se sostiene para pedir la ayuda; un error inaceptable sería sobreestimar ese ahorro.
En el modelo de climatización el objetivo es anticipar el consumo del día siguiente para programar el arranque de los equipos y evitar picos de potencia. «Mejorar el modelo» no es un
objetivo: hay que decir qué error se quiere reducir y quién lo paga.

Lo que no se sabe se nombra como desconocido («no sabemos si las horas de funcionamiento se cuentan dos veces»), no
se rellena con un supuesto silencioso.

## Contrato de datos

El contrato de datos es la lista de reglas que deben cumplir los datos antes de entrenar. Mínimo:

- Grano de la entidad: qué representa cada fila (una hora del edificio, un día de
  una máquina) y cuál es su clave. Si hay dos filas con la misma clave, hay un duplicado o un error.
- Momento de la etiqueta: cuándo se conoce el valor real que se quiere predecir. Una variable que
  solo se conoce después de ese momento no puede usarse para predecirlo.
- Fechas y zona horaria: formato de fecha explícito al leer, zona horaria declarada y cambios de
  hora revisados. Ejemplo (inventado): un servicio externo de previsión meteorológica entrega sus marcas de tiempo en UTC, mientras que los contadores del edificio están en hora local; en verano hay 2 h de desfase, y cruzarlos sin convertir empareja horas que no se corresponden.
- Columnas obligatorias, unidades (kWh frente a MWh, °C) y rangos razonables.
- Versión o instantánea del conjunto de datos usado, para poder rehacerlo.
- Datos sensibles o personales del cliente fuera de los artefactos, los registros y los ejemplos.

Ejemplo (inventado), en el estudio del compresor: a mitad de año el Excel de producción cambió el código del compresor (de «C-01» a «COMP-1»). El cruce INNER JOIN entre producción y consumos, por máquina y fecha, descartó en silencio todos los días posteriores al cambio: el segundo semestre se quedaba casi vacío. Se detecta contando los días cubiertos en cada mes, y se corrige en el código con una tabla de equivalencias de códigos, sin tocar el Excel original. Comprobaciones que lo habrían cazado antes: contar filas antes y después de cada cruce, contar los días cubiertos en cada mes y listar los códigos que no encuentran pareja.

Particiones por tiempo: el conjunto de validación sirve para elegir entre modelos y ajustes; el
de prueba se reserva para medir al final, una sola vez. En series temporales, ambos deben ser
posteriores al entrenamiento. Repartir filas al azar mete el futuro en el entrenamiento y da
métricas falsamente buenas.

Fuga de información (leakage): ocurre cuando el modelo ve, al entrenar, algo que no tendría al
predecir. Ejemplo: usar el consumo de la hora que se quiere predecir como variable. El modelo de climatización lo evita usando solo datos cerrados del día anterior, el calendario y la previsión meteorológica. Ante la duda, pregunta para
cada variable «¿la tendría en la mano en el momento de predecir?».

Hipótesis sobre variables: cada variable nueva debe venir con una razón («la ocupación de las oficinas explica la climatización necesaria») y con una pregunta sobre cómo podría filtrar el futuro. Decide
qué hacer con huecos (rellenar, descartar o tratarlos como información) y con valores atípicos
(investigar antes de recortar: un pico puede ser un fallo de sensor o un día real de producción).

`data/raw` es de solo lectura: los datos tal como llegaron del cliente o del sensor no se editan
nunca; se corrigen en código, que escribe en `data/processed` y se puede repetir.

## Baseline primero

Un baseline es un modelo de referencia tan sencillo que cualquier cosa más compleja debería
superarlo. Antes de un modelo complejo, monta dos:

1. Trivial: la persistencia («el valor dentro de una hora será igual al de ahora»), la media o el
   valor de la misma hora de la semana anterior. El modelo de climatización usa como referencia el consumo de la misma hora de la semana anterior, y cada modelo nuevo tiene que batirlo.
2. Simple: una regresión lineal con dos o tres variables con sentido físico (p. ej. consumo frente
   a producción).

Todo modelo nuevo se compara con ambos, con los mismos datos de validación y la misma métrica. Si
un gradient boosting (muchos árboles de decisión pequeños encadenados, cada uno corrigiendo al
anterior) o una red en PyTorch solo mejora un 1 % a la regresión, probablemente no compensa la
complejidad, y en un informe es más fácil defender el modelo simple.

## Evaluar antes de dar por buena una versión

Ninguna versión nueva (p. ej. una futura V4 del estudio del compresor) se da por buena ni se usa en un informe
hasta pasar esta evaluación:

- Métrica principal elegida con el usuario según el coste de los errores, no por costumbre. MAE
  (error absoluto medio) se lee en las unidades del problema; RMSE castiga más los errores
  grandes; R² dice qué parte de la variación explica el modelo; en clasificación, una matriz de
  confusión permite hablar de falsos positivos y falsos negativos concretos.
- Umbral decidido antes de ver los resultados: «la versión nueva se acepta si mejora al menos un
  5 % el MAE de la vigente y no empeora en ningún segmento».
- Resultados por segmentos: no solo la cifra global, también por mes, por máquina, por régimen de
  funcionamiento. Una mejora global puede esconder que un segmento importante empeora.
- Comparación con la versión anterior y con el baseline, en la misma tabla.
- Incertidumbre cuando hay pocos datos: con un R² modesto (p. ej. ≈0,5 en el consumo del modelo de climatización) o pocos
  meses de medida (p. ej. tres meses de un contador provisional en el estudio del compresor), da intervalos o la variación entre particiones, no una sola cifra con muchos decimales.
  Ejemplo (inventado), de la V2 a la V3 del estudio del compresor: la V2 daba un ahorro atribuible a la sustitución de 150.000 kWh/año, como una sola cifra y sin intervalo. La V3, con un modelo mejor que separa el efecto de la producción, da 50.000 kWh/año con un intervalo al 90 % de confianza de −30.000 a 130.000 kWh/año, que incluye el cero: con estos datos no se puede afirmar que la sustitución ahorre. Si el intervalo no incluyera el cero, para el informe se usaría la cifra conservadora (el límite inferior).
  El intervalo es lo que permite decir si
  una conclusión se sostiene, y un modelo mejor puede cambiarla.
- El conjunto de prueba no se usa para ajustar: si se mira muchas veces para elegir umbrales o
  hiperparámetros (ajustes que se fijan antes de entrenar, como la profundidad de los árboles),
  deja de ser una prueba independiente.

Si no pasa, la versión no se promociona: se documenta por qué y se sigue con la anterior.

## Análisis de errores

Después de cada entrenamiento o cambio importante:

1. Agrupa los errores grandes por rasgos comunes: fecha, mes, máquina, zona, fuente del dato.
2. Para cada grupo, busca la causa: un dato malo (sensor caído, fecha mal escrita), una etiqueta
   dudosa, una variable que falta (p. ej. un turno extra que no está en los datos) o un bug.
3. Decide el siguiente paso según la causa: arreglar el dato en código, añadir la variable,
   cambiar el umbral o aceptar el error y explicarlo en el informe.
4. Convierte cada error importante en una comprobación que se repite siempre: un test, un control
   de calidad del pipeline o un segmento fijo de la evaluación. Así el cambio de código del ejemplo anterior se
   convierte en un test que falla si alguien reconstruye la carga sin la corrección.
5. Escribe el siguiente experimento como algo que se pueda refutar («añadir la ocupación baja el MAE del consumo de la climatización»), no como «mejorar el modelo».

El ciclo bueno es: error → grupo → hipótesis → experimento → evidencia → sistema más simple.

## Registro de observaciones

En cada iteración se apunta, en pocas líneas:

```text
Iteración / versión:
Datos usados (fichero, versión, fecha de corte):
Versión del código (commit de git o fecha) y del entorno:
Qué cambió y por qué:
Métricas (global y por segmentos) frente a la versión anterior:
Errores nuevos o inesperados:
Decisión tomada y qué se acepta a cambio:
Comprobación añadida:
Siguiente paso:
```

Dónde se guarda:
- En la entrada de sesión de la skill `journal` al cerrar la jornada.
- En estudios, además, en la memoria de trazabilidad del proyecto (p. ej. la memoria de la versión vigente), que es lo que permite defender cada cifra del informe.
- Si el proyecto usa MLflow (registro de experimentos: parámetros, métricas y modelos de cada
  ejecución) o DVC (versionado de ficheros de datos y modelos junto a git), el registro remite a
  ellos.

## Si el modelo se re-ejecuta o está en producción

- Idempotencia: cada fase lee de una entrada fija y escribe en una salida con nombre propio
  (por versión o fecha de corte); relanzarla no duplica ni mezcla resultados.
- Configuración fuera del código: rutas, fechas de corte, semilla aleatoria (el número que fija
  el azar para que dos ejecuciones den lo mismo) e hiperparámetros en un fichero de
  configuración, no escritos a mano en el script ni en un notebook.
- Versiones de paquetes fijadas (requirements: el fichero que lista las librerías y su versión
  exacta) y versión del código apuntada con cada resultado.
- Comprobación de deriva de los datos nuevos: antes de predecir, comparar rangos, huecos y
  distribución de las variables principales con los de entrenamiento; si se salen, avisar en vez
  de predecir en silencio.
- Versión identificable: el artefacto del modelo guarda su versión, los datos con que se entrenó,
  la configuración y el preprocesado; y cada salida (Excel o respuesta de la API) dice qué versión
  la generó.
- Mismo preprocesado al entrenar y al predecir: que salga del mismo código, no de una copia.
- Contrato de entrada y salida: validar columnas, tipos, unidades, zona horaria y rangos a la
  entrada; rechazar lo inválido con un mensaje claro.
- Vuelta atrás: se conserva el artefacto anterior y se puede volver a él cambiando una línea de
  configuración, sin reentrenar.
- En producción, además, monitorización de la calidad de los datos y de las predicciones, no solo
  de que el servicio esté levantado.

En un proyecto que combina el modelo propio con datos de un servicio externo (p. ej. la previsión meteorológica), ese contrato es lo más delicado: el servicio externo se usa en solo lectura, no se modifica, y se comprueba lo que devuelve (horas completas, unidades, conversión de UTC a hora local).

## Organización por versiones

- Una carpeta por versión en la raíz del proyecto, con su nombre habitual: «modelo VNN» (p. ej.
  «modelo V3» en el estudio del compresor).
- Dentro va todo lo de esa versión: modelo, trazabilidad, justificación, informe, presentación y
  entrega. Así, quien abre la carpeta ve la versión completa y no mezcla cifras de dos versiones.
- Solo las 2 últimas versiones quedan a la vista; las anteriores se mueven a «obsoleto/».
- No hay carpetas transversales en la raíz tipo «final/» o «entrega»: lo entregado vive dentro
  de la versión de la que salen sus cifras. «reports/» queda solo para documentos generales del proyecto.

## Hitos y revisión

Los hitos son: cerrar una versión de modelo, cerrar un informe y cerrar un entregable. Antes de
cada uno:

1. Lanza el agente `mle-reviewer` (solo lectura) sobre el proyecto.
2. Enseña sus hallazgos al usuario, ordenados por gravedad.
3. El usuario decide qué se corrige antes del hito y qué se acepta y se documenta.

No se corrige nada por cuenta propia a partir de la revisión sin que el usuario lo vea antes.

## Con qué herramientas se combina

| Fase | Herramienta |
|---|---|
| Estructura de carpetas y fases del pipeline | `ml-pipeline-workflow` |
| Diseñar el enfoque y planificar | `brainstorming`, `writing-plans` |
| Transformaciones de datos y cálculo de métricas | `test-driven-development` |
| Algo no cuadra (métrica rara, datos que no casan) | `systematic-debugging` |
| Antes de afirmar un resultado o cerrar una tarea | `verification-before-completion` |
| Exploración, modelado e industrialización | agentes `data-scientist`, `ml-engineer`, `mlops-engineer` |
| Revisión en los hitos | `mle-reviewer` |
| Entregar resultados (Excel, Word, gráficos) | `xlsx`, `docx`, `dataviz` |
| Dejar rastro y tareas pendientes | `journal`, `/tasks` |

## Errores frecuentes

- Reproducir el modelo exige el estado de un notebook que nadie sabe rehacer.
- Partición aleatoria en una serie temporal: el futuro entra en la validación.
- Cruces (JOIN) que descartan filas en silencio sin contar cuántas se pierden (el cambio de código del ejemplo anterior dejó medio año casi vacío).
- Corregir a mano los Excel originales del cliente en vez de corregir en código.
- Mezclar horas en UTC y hora local sin convertir.
- Mejora global de la métrica que esconde que un segmento importante empeora.
- Ajustar umbrales mirando una y otra vez el conjunto de prueba.
- Una sola cifra con muchos decimales cuando los datos dan para mucha menos precisión.
- Copiar a mano el preprocesado del entrenamiento en el script de predicción.
- Salidas sin versión de modelo: no se sabe qué modelo generó el Excel de un mes.
- Una cifra del informe o del entregable que nadie sabe de qué versión salió.
- Volver atrás exige reentrenar porque no se guardó el artefacto anterior.
- Rellenar con supuestos lo que no se sabe en vez de decirlo.
- Añadir complejidad (más variables, un modelo profundo) sin que el análisis de errores diga por qué.

Adaptado de ECC (MIT) — https://github.com/affaan-m/ECC, skill mle-workflow.
