---
title: "Guía práctica de Arquitectura de Información para aplicaciones multimedia educativas"
source: "https://www.nosolousabilidad.com/articulos/guia_ai.htm"
author:
  - "[[Jessica Arencibia Cobas]]"
  - "[[Yuniet del Carmen Toll Palma]]"
  - "[[José Antonio Soto Pérez]]"
  - "[[Deymis Tamayo Rueda]]"
  - "[[Yenieris Moyares Norchales]]"
  - "[[Yohandri Ril Gil]]"
published:
created: 2026-07-25
description: "Las guías prácticas de arquitectura de información se presentan como una herramienta orientada a mejorar procesos de arquitectura de información y la capacitación de los profesionales involucrados. En el presente trabajo se propone una guía práctica de arquitectura de información para aplicaciones multimedia educativas incluyendo ejemplos prácticos de las diferentes etapas y técnicas."
tags:
  - "clippings"
---
no solo usabilidad: revista sobre personas, diseño y tecnología

menú

Arencibia Cobas, Jessica  
Toll Palma, Yuniet del Carmen  
Soto Pérez, José Antonio  
Tamayo Rueda, Deymis  
Moyares Norchales, Yenieris  
Ril Gil, Yohandri

> **Resumen:** Las guías prácticas de arquitectura de información se presentan como una herramienta orientada a mejorar procesos de arquitectura de información y la capacitación de los profesionales involucrados. En el presente trabajo se propone una guía práctica de arquitectura de información para aplicaciones multimedia educativas incluyendo ejemplos prácticos de las diferentes etapas y técnicas.

## Introducción

Desde el año 2007 en la Universidad de las Ciencias Informáticas (UCI) se viene prestando especial atención a la investigación en el área de la Arquitectura de Información, por su importancia crucial como medio para proporcionar una experiencia de usuario satisfactoria.

Entre las funciones del Centro de Tecnologías para la Formación (FORTES) de la UCI se encuentra el desarrollo de aplicaciones multimedia educativas, pero se observa que quienes desempeñan el rol de arquitectos de información no poseen los suficientes conocimientos necesarios sobre la temática, por lo que las aplicaciones desarrolladas terminan presentando algunos problemas de organización y recuperación de información, usabilidad y, consecuentemente, problemas de asimilación de los contenidos por parte de los usuarios finales.  
  
El objetivo de este trabajo es presentar una guía práctica de arquitectura de información que mejore el resultado de desarrollo de aplicaciones multimedia educativas en términos usabilidad y aceptación por parte de los usuarios finales, además de servir como herramienta de capacitación de los profesionales involucrados.

## Guía práctica

Las guías prácticas suponen una herramienta de ayuda y soporte en el proceso de elaboración de arquitecturas de información, en las que se definen las actividades, técnicas y recomendaciones aplicables en cada etapa del proceso. La presente guía se estructura en dos fases principales: "Inicio de la arquitectura de información" y "Desarrollo de la arquitectura de información".

![diagrama de flujo de actividades](https://www.nosolousabilidad.com/articulos/img/guia1.png) **Fig. 1**. Flujo de actividades de las dos fases de la guía práctica.

### Fase 1. Inicio de la Arquitectura de información

Esta fase está compuesta por cuatro actividades diferentes: recopilación de información, definición de los objetivos, definición de la audiencia y el inventario de contenidos.

#### Recopilación de Información

**Técnicas a utilizar**: Entrevistas y encuestas para conocer las necesidades del cliente y los usuarios.

**Recomendaciones**:

- El arquitecto de información debe involucrarse en el proyecto desde la fase inicial del proceso de desarrollo, para obtener así la información necesaria sobre el producto que se desea implementar.
- Debe tener presente las metodologías de desarrollo que se utilizan, tales como Rational Unified Process (RUP) o eXtreme Programming (XP), para participar en las reuniones con el cliente desde que se inicia el contrato del producto.
- Dependiendo de si el cliente es nacional o internacional se considerará si es posible su participación directa en el proceso o, por el contrario, el arquitecto de información actuará como intermediario.
- Se deben realizar estudios de la audiencia: análisis contextual y estudio del entorno social, cultural y lingüístico del público objetivo.
- Se debe realizar un análisis competitivo de las tecnologías y herramientas similares al producto que se pretende desarrollar, con el objetivo de detectar tanto carencias extendidas como buenas prácticas de diseño en este tipo de productos. Los indicadores que se debe tener principalmente en cuenta son: Organización de la información, Sistema de navegación, Etiquetado y Diseño gráfico.
- Para recopilar información se pueden realizar las preguntas siguientes:
	- ¿Qué edad tiene los alumnos que utilizan la aplicación educativa?
		- ¿Conocen los alumnos qué es una aplicación multimedia educativa?
		- ¿Han interactuado antes con este tipo de producto?
		- ¿Qué otras personas pueden utilizar estas aplicaciones?
		- ¿Qué conocimientos tecnológicos tienen los alumnos?
		- ¿Qué contenidos son los más relevantes para el aprendizaje? ¿Por qué?
		- ¿Existe algún material u objeto de aprendizaje utilizado anteriormente para la comprensión o estudio de la materia que va a abordar la aplicación?
- El arquitecto de información debe participar junto con el analista en todo momento en el que se interactué con el cliente o el público objetivo.

#### Definición de los objetivos

**Técnicas a utilizar**: Realizar preguntas enfocadas a los alumnos para determinar cuál es el propósito de la aplicación a desarrollar.

**Recomendaciones**:

- Las preguntas pueden ser:
	- ¿Cuál es el objetivo de esta aplicación multimedia?
		- ¿Qué nivel de aprendizaje alcanzarán los alumnos?
		- ¿Qué habilidades desarrollarán los alumnos con el uso de de este producto?
		- ¿Qué contenidos educativos se ofrecerán en la aplicación? En esta pregunta ya se está evidenciando un primer momento del inventario de contenidos, imprescindible para la taxonomía y el sistema de navegación. Para que el inventario de contenido sea el adecuado el arquitecto de información debe asegurarse de que obtiene todos los datos de localización y acceso a los contenidos educativos para su posterior utilización.
		- ¿Qué servicios de entretenimiento e interacción ofrecerá la aplicación para captar el interés de los alumnos? Con esta pregunta se aborda la denominada expectativa del usuario, pues aunque no forma parte de las funcionalidades básicas de la aplicación, se pretende con esto que la misma tenga altos índices de usabilidad.
- Identificar requisitos funcionales: los requisitos funcionales que se identifiquen mediante las preguntas anteriores sirven para conocer los contenidos que debe ofrecer la aplicación, información que será útil para realizar el inventario de contenidos y para el desarrollo de los prototipos de la interfaz. Por ejemplo:
	- Mostrar cuentos infantiles de diferentes autores.
		- Realizar juegos de matemáticas (pueden ser rompecabezas, crucigramas entre otros para medir el conocimiento).
		- Ver imágenes sobre los personajes de los cuentos.
		- Ver videos para aprender a conjugar palabras.

#### Definición de la audiencia

**Técnicas a utilizar**: Estudio de usuarios para conocer las necesidades y características de los alumnos que van a utilizar la aplicación. Se pueden utilizar encuestas, entrevistas y técnicas de card sorting.

**Recomendaciones**:

- Existen metodologías que pueden ser aplicables para realizar esta actividad y que tienen su base en la bibliotecología, tal es el caso de la metodología AMIGA. Es una metodología integral para la determinación y la satisfacción dinámica de las necesidades de formación e información en las organizaciones y comunidades. El arquitecto de información puede hacer uso de la misma para conocer las necesidades de los usuarios/clientes en la organización atendiendo a su diversidad, para luego diseñar un producto homogéneo que se ajuste a las diferencias de los mismos [(Núñez-Paula](#biblio); 2005).
- El arquitecto de información debe conocer las necesidades y características de los alumnos que van a utilizar la aplicación, es importante que conozca el ámbito social en el que se encuentran así como características de su comportamiento, pues los alumnos requieren de recursos atractivos como animaciones, videos, imágenes y temas de interés, y estos son elementos que se deben tener en cuenta para realizar un diseño interactivo de interés para los mismos.
- El arquitecto de información debe clasificar la audiencia atendiendo a:
	- Capacidad física: en este caso puede realizar encuestas para ver si existen usuarios con discapacidades físicas. La aplicación debe incluir diferentes formas de presentación de la información (sonido con texto incluido en caso de los alumnos que sean ciegos, imágenes y textos para el caso de los alumnos que sean sordos), con el fin de no excluir a ningún alumno.
		- Capacidad técnica: se debe valorar si es necesario dividir en grupos a los usuarios en función de sus conocimientos tecnológicos.
		- Ubicación geográfica: se debe tener en cuenta la diversidad cultural, idioma, etc.
- El arquitecto de información debe entrevistarse con el cliente y con el público objetivo, y hacerle preguntas directas para conocer lo que desean y esperan de la aplicación. Las preguntas que puede realizar son:
	- ¿Qué ventajas les brinda la aplicación educativa a los alumnos?
		- ¿Qué facilidades podrán tener los alumnos con su uso?
		- ¿Qué le gustaría ver en la aplicación multimedia educativa?

#### Inventario de contenidos

**Técnicas a utilizar**: Entrevistas

**Recomendaciones**:

- El arquitecto de información debe ser exhaustivo durante las entrevistas con el cliente para obtener información sobre los contenidos que se desean ofrecer en la aplicación.
- Por lo general, en las aplicaciones educativas, quien se encarga de la selección y adquisición de los contenidos es el diseñador instruccional o el experto en contenido, por lo que el arquitecto de información se valdrá de la información que le proporcionará el diseñador instruccional para su inventario.
- Para obtener información puede realizar las siguientes preguntas:
	- ¿Dónde se encuentra el contenido?
		- ¿En qué formato se encuentra?
		- ¿Hay expertos en el tema de esa asignatura?
		- El contenido tiene audio, video, imágenes, gráficos?
- Completar la plantilla del inventario de contenidos con los campos siguientes:
	- Nº: número de orden en que son registrados los contenidos.
		- Nivel: número que indica a qué contenido pertenece.
		- Contenido: nombre del contenido.
		- Descripción: breve resumen del contenido.
		- Elemento multimedia: especificar el/los tipo(s) de elemento(s) multimedia que tendrá el contenido. Por ejemplo: gráficos, fotografías, animaciones, vídeos, voz, música, texto, …
		- Formato: formato en que se encuentran los elementos multimedia. Si es mp3, rmv, jpg, png, doc, gif …

En la siguiente tabla se muestra un ejemplo del inventario de contenidos.

<table><tbody><tr><td colspan="9"><p><strong>Inventario de contenidos y servicios para las multimedia educativas</strong></p></td></tr><tr><td colspan="4"><p><strong>Nombre del Software</strong> <strong>: Colección “El navegante”</strong></p></td><td colspan="5"><p><strong>Centro de producción:</strong> Universidad de las Ciencias Informáticas.</p></td></tr><tr><td><p><strong>Nº</strong></p></td><td><p><strong>Nivel</strong></p></td><td colspan="2"><p><strong>Contenido</strong></p></td><td><p><strong>Descripción</strong></p></td><td colspan="2"><p><strong>Elemento multimedia</strong></p></td><td colspan="2"><p><strong>Formato</strong></p></td></tr><tr><td><p>1</p></td><td></td><td colspan="2"><p>Inicio</p></td><td><p>Sección para acceder a la aplicación.</p></td><td colspan="2"><p>Imágenes</p></td><td colspan="2"><p>jpg</p></td></tr><tr><td><p>2</p></td><td><p>1</p></td><td colspan="2"><p>Contenido</p></td><td><p>Diferentes temas relacionados con la cultura general.</p></td><td colspan="2"><p>Texto</p></td><td colspan="2"></td></tr><tr><td><p>3</p></td><td><p>2</p></td><td colspan="2"><p>El lenguaje del arte</p></td><td><p>Un resumen acerca de este tema para conocimiento del usuario.</p></td><td colspan="2"><p>Texto</p></td><td colspan="2"></td></tr><tr><td><p>4</p></td><td><p>3</p></td><td colspan="2"><p>El disfrute de las manifestaciones artística</p></td><td><p>Un resumen acerca de este tema para conocimiento del usuario.</p></td><td colspan="2"><p>Texto, imágenes</p></td><td colspan="2"><p>jpg</p></td></tr><tr><td><p>5</p></td><td><p>1</p></td><td colspan="2"><p>Ejercicios</p></td><td><p>Diferentes ejercicios relacionados con la cultura general donde el usuario pueda escoger el tema.</p></td><td colspan="2"><p>Texto</p></td><td colspan="2"></td></tr><tr><td><p>6</p></td><td><p>5</p></td><td colspan="2"><p>Ejercicio 1 El lenguaje del arte</p></td><td><p>Un ejercicio acerca de este tema.</p></td><td colspan="2"><p>Texto, imágenes</p></td><td colspan="2"><p>jpg</p></td></tr><tr><td><p>7</p></td><td><p>5</p></td><td colspan="2"><p>Ejercicio 2 La danza</p></td><td><p>Un ejercicio acerca de este tema.</p></td><td colspan="2"><p>Texto, imágenes</p></td><td colspan="2"><p>jpg</p></td></tr><tr><td><p>8</p></td><td><p>1</p></td><td colspan="2"><p>Mediateca</p></td><td><p>Diferentes opciones recreativas, el usuario debe seleccionar sobre qué tema desea la opción recreativa.</p></td><td colspan="2"><p>Texto, imágenes</p></td><td colspan="2"><p>jpg</p></td></tr><tr><td><p>9</p></td><td><p>8</p></td><td colspan="2"><p>Video</p></td><td><p>Diferentes videos sobre el tema escogido.</p></td><td colspan="2"><p>Texto, imágenes, video.</p></td><td colspan="2"><p>jpg, rmv</p></td></tr><tr><td><p>10</p></td><td><p>8</p></td><td colspan="2"><p>Animaciones</p></td><td><p>Diferentes animaciones sobre el tema escogido.</p></td><td colspan="2"><p>Texto, imágenes, animaciones.</p></td><td colspan="2"><p>jpg, rmv, flv.</p></td></tr><tr><td><p>11</p></td><td><p>1</p></td><td colspan="2"><p>Juegos</p></td><td><p>Diferentes juegos</p></td><td colspan="2"><p>Texto, imágenes.</p></td><td colspan="2"><p>jpg</p></td></tr><tr><td><p>12</p></td><td><p>11</p></td><td colspan="2"><p>Crucigramas</p></td><td><p>Los crucigramas, el usuario debe seleccionar el tema del mismo.</p></td><td colspan="2"><p>Texto, imágenes</p></td><td colspan="2"><p>jpg</p></td></tr><tr><td><p>13</p></td><td><p>12</p></td><td colspan="2"><p>Crucigrama Arte italiano</p></td><td><p>El crucigrama sobre el tema escogido.</p></td><td colspan="2"><p>Texto, imágenes, animaciones.</p></td><td colspan="2"><p>jpg, rmv, flv.</p></td></tr><tr><td colspan="9"></td></tr><tr><td colspan="3"><p><strong>Realizado por:</strong> Jessica Arencibia Cobas</p></td><td colspan="3"><p><strong>Dirigido a:</strong> Enseñanza secundaria de la República Bolivariana de Venezuela</p></td><td colspan="3"><p><strong>Fecha:</strong> 15/03/2011</p></td></tr></tbody></table>

### Fase 2. Desarrollo de la Arquitectura de Información

Esta segunda fase se compone de cuatro actividades fundamentales: estructura o taxonomía, sistema de etiquetado, sistema de navegación y diseño de las pantallas base.

#### Estructura o Taxonomía

**Recomendaciones**:

- Para realizar la taxonomía debe tener presente los requisitos funcionales del producto y además la información obtenida mediante el inventario de contenidos.
- Debe tener en cuenta que los contenidos educativos deben representarse en un orden lógico mediante una estructura que permita localizarlos fácilmente y evite que los usuarios se sientan desorientados o desmotivados.
- Debe utilizar un modelo taxonómico que refleje la relación entre los contenidos y la ubicación exacta de los mismos dentro de las secciones de la aplicación.
- Se recomienda que utilice un modelo jerárquico simple, pues ofrece una forma fácil y familiar de organizar el contenido.

A continuación se muestra un ejemplo de taxonomía jerárquica:

1\. Inicio  
1.1 Contenido  
1.1.1 El lenguaje del arte  
1.1.1.1 El disfrute de las manifestaciones artísticas  
1.1.2 La música y su lenguaje sonoro  
1.1.3 Las artes visuales como sistema de comunicación  
1.1.4 La danza  
1.1.5 El teatro  
1.1.6 El cine  
1.2 Ejercicios  
1.2.1 El lenguaje del arte  
1.2.2 La música y su lenguaje sonoro  
1.2.3 Las artes visuales como sistema de comunicación  
1.2.4 La danza  
1.2.5 El teatro  
1.2.6 El cine  
1.3 Mediateca  
1.3.1 Videos  
1.3.1.1 Video 1El lenguaje del arte  
1.3.1.2 Video 2 La música y su lenguaje sonoro  
1.3.2 Animaciones  
1.3.3 Imágenes  
1.3.4 Diaporamas  
1.3.5 Sonido  
1.3.6 Glosario  
1.3.7 Personalidades y laboratorio  
1.4 Juegos  
1.4.1 Crucigrama  
1.4.1.1 Crucigrama 1 El lenguaje del arte  
1.4.1.2 Crucigrama 2 La música y el lenguaje sonoro  
1.4.2 Descubre la imagen  
1.4.3 Sopa de letras  
1.4.4 Ludo

#### Definir el sistema de etiquetado

**Técnicas a utilizar**: Etiquetado: definir las etiquetas que tendrá la aplicación con el propósito de observar los términos en el contexto de uso.

**Recomendaciones**:

- Debe definir el sistema de etiquetado basándose en los objetivos del cliente y las características de los usuarios.
- Debe centrarse en el público objetivo (alumnos). Las etiquetas deben ser de fácil identificación e interpretación, utilizando para ello un vocabulario comprensible por los usuarios.
- Debe definir las etiquetas según su clasificación, seguido del nombre de la etiqueta y la función que realiza (botón, vínculo, encabezado de sección). Las etiquetas se clasifican en:
	- Etiquetas de navegación (EN): pueden utilizarse para señalar acciones a realizar por el alumno, por ejemplo: para que regrese a un contenido (“Volver atrás”), para que siga adelante (“Siguiente”), para salir de la aplicación (“Salir”).
		- Etiquetas de enlaces (EE): pueden utilizarse dentro de los párrafos o en cualquier otro lugar de la aplicación. Pueden ser destacadas o subrayadas para llamar la atención de los alumnos con colores fuertes o claros dependiendo del color de fondo de la aplicación.
		- Etiquetas del sistema de cabeceras o títulos (ET): funcionan como títulos, se pueden utilizar para mostrar un significado previo del contenido a tratar. Son etiquetas que reflejarán dónde se encuentra el alumno en cada momento, qué sección está viendo.
		- Etiquetas del sistema de indización: son invisibles para el usuario, pueden utilizarse para facilitar la búsqueda sobre un contenido determinado. El usuario por medio de palabras claves hace una consulta sobre una información y la aplicación le devuelve los enlaces de los documentos que contienen las palabras clave introducidas.

Se presenta un ejemplo del sistema de etiquetado.

Etiquetas de navegación:

- Aceptar: indica entrar a un contenido determinado.
- Volver: indica retornar al contenido anterior.
- Comenzar: indica empezar un ejercicio determinado
- Siguiente: indica continuar hacia el próximo contenido.
- Terminar: indica finalizar un ejercicio determinado.

Etiquetas de enlaces:

- Noticias: vínculo al texto noticas.
- Efemérides: vínculo al texto efemérides.
- Sabías que: vínculo al texto curiosidades.
- Revisa tu respuesta: vínculo al gráfico de respuesta.
- Crucigrama: vínculo a los crucigramas.

Etiquetas del sistema de cabeceras o títulos:

- Contenido: título de la sección de contenido.
- Noticias: título la sección de noticias.
- Elementos matemáticos: título de todas las secciones de la multimedia.
- Ejercicios: titulo de la sección ejercicios.
- Mediateca: título de la sección mediateca.

Etiquetas del sistema de indización:

- Música: permite listar todos los contenidos relacionados con el tema.
- Pintura: permite listar todos los contenidos relacionados con el tema.
- Juegos: permite listar todos los juegos.

#### Definir el sistema de navegación (SN)

**Recomendaciones**:

- El arquitecto de información no podrá realizar esta actividad sin haber definido previamente la taxonomía, ya que el sistema de navegación está condicionado por la taxonomía.
- Debe definir un SN que permita a los alumnos navegar fácilmente de una sección a otra. Para ello el sistema de navegación debe ayudar al usuario a reconocer qué contenido se encuentra consultando, qué secciones ya ha visitado y qué opciones de navegación tiene. Esto se materializa, por ejemplo, con el cambio de color en los enlaces ya visitados, o resaltando la sección en la que se encuentra con el cambio de color en la fuente.
- Se recomienda que utilice un SN global para que el alumno pueda navegar por los diferentes contenidos de forma ágil.
- En el SN el arquitecto de información debe tener en cuenta los siguientes elementos:
	- Menú General: siempre presente en toda la aplicación multimedia, permite el acceso a cada una de las secciones de la misma.
		- Botones: siempre presente para indicar acciones (entrar, salir, continuar, volver entre otros).
		- Menús desplegables.
		- Barras de desplazamiento.
		- Hipervínculos o enlaces.
		- Rutas de acceso: permite orientar al alumno acerca de la ubicación del contenido que se encuentra consultando en cada momento.
		- Buscador.
		- Botón Ayuda.
		- Botón imprimir.
- Tras definir los elementos que componen el SN, el arquitecto de información debe crear el mapa de navegación que brinde al cliente y los desarrolladores una visión detallada de cómo será la navegación de los contenidos educativos.
- Entre las herramientas para crear mapas de navegación, recomendamos el uso de Cmap Tools.

En la siguiente figura se detalla un ejemplo del mapa de navegación. Este mapa de navegación contiene las rutas o caminos de acceso a los diferentes contenidos que se mostrarán en la aplicación multimedia educativa “El navegante”.

![diagrama de navegación](https://www.nosolousabilidad.com/articulos/img/guia2.png)

#### Definir las pantallas base

**Técnicas a utilizar:** Entrevista, para definir las características visuales del producto. Diagramación, consiste en realizar diagramas con la información organizada, representando la estructura y funcionamiento de la aplicación.

**Recomendaciones**:

- Debe reunirse con el cliente para definir las características visuales del producto, y debe tener en cuenta los requisitos funcionales y el estudio que realizó sobre las necesidades y expectativas del público objetivo durante la recopilación de información.
- Tras definir las características visuales del producto, el arquitecto de información debe diseñar las pantallas base. Para ello se recomienda que utilice el diagrama de presentación, que permite mostrar cómo está organizada la información de las principales secciones de la aplicación, y donde el cliente y el resto del equipo de desarrollo pueden ver las prioridades organizativas y los elementos visuales más importantes.
- Se deben realizar tantos diagramas como sean necesarios, normalmente uno por cada sección de la aplicación.
- Para diseñar las pantallas base se recomienda utilizar la herramienta OpenofficeDraw.
- Tras definir las pantallas base, el arquitecto de información debe reunirse con el cliente y los desarrolladores (en este caso también pueden participar usuarios reales) para presentarles el diseño general de la aplicación. Las opiniones e ideas que surjan durante la presentación pueden ayudar al arquitecto de información a mejorar el diseño.

Ejemplos del diagrama de presentación:

![ejemplo de wireframe](https://www.nosolousabilidad.com/articulos/img/guia3.png)

## Conclusiones

En este trabajo se ha propuesto una guía práctica de arquitectura de información orientada al desarrollo de aplicaciones multimedia educativas. Los diferentes profesionales que hasta la fecha han hecho uso de la guía han mostrado una amplia satisfacción, y expertos consultados han avalado el interés y validez de la misma. Como futuras líneas de trabajo se pretende estandarizar la guía para capacitar, en cuestiones de arquitectura de información, no sólo a los propios arquitectos de información, sino también a todo el equipo de desarrollo.

## Bibliografía

**Almira, P., (2010)**. Propuesta de Arquitectura de Información del proyecto productivo Sistema de Gestión Fiscal (SGF). La Habana: s.n., 2010.

**Almira, P., (2010)**, Trabajo de Diploma "Propuesta de Arquitectura de Información del proyecto productivo Sistema de Gestión Fiscal (SGF).". Ciudad de la Habana: s.n., 2010.

**Amador, A. (2009)**, Trabajo de Diploma Arquitectura de Información del Módulo Dirección Técnica para el “Sistema de Gestión de la Producción”. Ciudad Habana: s.n., Junio 2009.

**Belloch Ortí, C. (2010)**, Universidad de Valencia. APLICACIONES MULTIMEDIA INTERACTIVAS. \[En línea\] 2010. \[Citado el: 18 de 04 de 2011.\]  
[http://www.uv.es/bellochc/pdf/pwtic3.pdf](http://www.uv.es/bellochc/pdf/pwtic3.pdf)

**Carcés, Rosales, A. (2009)**, Procedimiento para la definición y ejecución de la Arquitectura de Información de los Productos del Polo PetroSoft. Ciudad de la Habana: s.n., 2009.

**Chile, Ministerio Secretaría General de Gobierno de.** (2004), Guía para desarrollo de Sitios Web. Santiago de Chile: s.n., Enero 2004. Disponible en:  
[http://www.guiaweb.gob.cl/](http://www.guiaweb.gob.cl/)

**Fernández Hernández, A., (2007),** Organización de los contenidos en los sitios Web: las taxonomías. \[En línea\] 30 de 03 de 2007. \[Citado el: 21 de 03 de 2011.\]  
[http://bvs.sld.cu/revistas/aci/vol15\_05\_07/aci12507.htm](http://bvs.sld.cu/revistas/aci/vol15_05_07/aci12507.htm)

**Garrido, J., Mannarelli, M. (2011),**  
Inventario de contenidos. \[En línea\] \[Citado el: 21 de 03 de 2011.\]  
[http://www.arquitecturadeinformacion.cl/como/inventario.html](http://www.arquitecturadeinformacion.cl/como/inventario.html)

**Hassan, Y., Martín Fernández, F., Iazza, G., (2004)**. Diseño Web Centrado en el Usuario: Usabilidad y Arquitectura de la Información. \[En línea\] \[Citado el: 19 de enero de 2011.\] Disponible en:  
[http://www.upf.edu/hipertextnet/numero-2/diseno\_web.html](http://www.upf.edu/hipertextnet/numero-2/diseno_web.html)

**Hernández, S., (2009),** Propuesta de procedimiento para definir la Arquitectura de Información en los productos del polo Geoinformática de la facultad 9. Ciudad de la Habana: s.n., 2009.

**Infante, M., (2008)**, Trabajo de Diploma: Propuesta y análisis de la Arquitectura de Información en el proyecto CICPC. Ciudad de La Habana: s.n., 2008.  
  
**INTECO, Instituto Nacional de Tecnologías de la Comunicación. (2008)**, Guías Prácticas de Comprobación de Accesibilidad: HERRAMIENTAS DE EVALUACIÓN DE LA ACCESIBILIDAD WEB. Marzo 2008.

**Núñez-Paula, I. (2005),** AMIGA: una metodología integral para la determinación y la satisfacción dinámica de las necesidades de formación e información en las organizaciones y comunidades. \[En línea\] 15 de 10 de 2005. \[Citado el: 05 de 02 de 2011.\] Disponible en:  
[http://bvs.sld.cu/revistas/aci/vol12\_4\_04/aci02404.htm](http://bvs.sld.cu/revistas/aci/vol12_4_04/aci02404.htm)

**Pérez Montoro, M. (2011)**. Arquitectura de la información en entornos web. El profesional de la información, ISSN 1386-6710, Vol. 19, Nº 4, 2010, pp. 333-338

**Ronda León, R., (2005),** La Arquitectura de la Información y las Ciencias de la Información. No solo usabilidad. \[En línea\] 25 de 04 de 2005. \[Citado el: 15 de 01 de 2011.\] Disponible en:  
[http://www.nosolousabilidad.com/articulos/ai\_cc\_informacion.htm](http://www.nosolousabilidad.com/articulos/ai_cc_informacion.htm)

**Sablón Fernández Y., Hernández Aballe, D., (2008),** Trabajo de Diploma: Propuesta de un proceso para realizar la Arquitectura de Información en los proyectos productivos de la Universidad de las Ciencias Informáticas. Ciudad de la Habana: s.n., Junio 2008.

**Jessica Arencibia Cobas**

Ing. Universidad de las Ciencias Informáticas (UCI), Cuba.

**Yuniet del Carmen Toll Palma**

MSc. Universidad de las Ciencias Informáticas (UCI), Cuba.

**José Antonio Soto Pérez**

Ing. Universidad de las Ciencias Informáticas (UCI), Cuba.

**Deymis Tamayo Rueda**

Lic. Universidad de las Ciencias Informáticas (UCI), Cuba.

**Yenieris Moyares Norchales**

Lic. Universidad de las Ciencias Informáticas (UCI), Cuba.

**Yohandri Ril Gil**

Ing. Universidad de las Ciencias Informáticas (UCI), Cuba.

**Citación recomendada:**

Arencibia Cobas, Jessica; Toll Palma, Yuniet del Carmen; Soto Pérez, José Antonio; Tamayo Rueda, Deymis; Moyares Norchales, Yenieris; Ril Gil, Yohandri (2012). Guía práctica de Arquitectura de Información para aplicaciones multimedia educativas. En: No Solo Usabilidad, nº 11, 2012. <nosolousabilidad.com>. ISSN 1886-8592

No Solo Usabilidad - ISSN 1886-8592. Todos los derechos reservados, 2003-2026  
email: info (arroba) nosolousabilidad.com