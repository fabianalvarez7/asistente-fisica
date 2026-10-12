"""Generate the shareable exercise-catalog guide without external dependencies."""

from pathlib import Path
from textwrap import wrap


PAGE_W, PAGE_H = 595, 842
LEFT, RIGHT = 58, 537


def pdf_text(value: str) -> bytes:
    encoded = value.encode("cp1252", errors="replace")
    return b"(" + encoded.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)") + b")"


def line_commands(lines: list[tuple[str, str]]) -> bytes:
    commands = [b"q", b"0.15 0.25 0.31 rg", b"BT"]
    y = PAGE_H - 60
    for kind, text in lines:
        if kind == "title":
            commands.extend([b"/F2 22 Tf", f"1 0 0 1 {LEFT} {y} Tm".encode(), pdf_text(text), b"Tj"])
            y -= 34
        elif kind == "subtitle":
            commands.extend([b"0.35 0.48 0.54 rg", b"/F1 11 Tf", f"1 0 0 1 {LEFT} {y} Tm".encode(), pdf_text(text), b"Tj", b"0.15 0.25 0.31 rg"])
            y -= 28
        elif kind == "heading":
            y -= 8
            commands.extend([b"0.12 0.37 0.46 rg", b"/F2 14 Tf", f"1 0 0 1 {LEFT} {y} Tm".encode(), pdf_text(text), b"Tj", b"0.15 0.25 0.31 rg"])
            y -= 22
        else:
            prefix = "• " if kind == "bullet" else ""
            size = 9 if kind == "code" else 10
            indent = LEFT + (14 if kind == "bullet" else 0)
            width = 82 if kind == "bullet" else 92
            for index, part in enumerate(wrap(prefix + text, width=width)):
                commands.extend([f"/F1 {size} Tf".encode(), f"1 0 0 1 {indent} {y} Tm".encode(), pdf_text(part), b"Tj"])
                y -= 14
                if y < 58:
                    break
            y -= 4
        if y < 58:
            break
    commands.extend([b"ET", b"Q"])
    return b"\n".join(commands)


def make_pdf(path: Path) -> None:
    pages = [
        [("title", "Cómo incorporamos ejercicios al asistente"), ("subtitle", "Propuesta de trabajo para Física 1"),
         ("heading", "Idea principal"), ("body", "El asistente no resolverá problemas de física arbitrarios. Solo trabajará con ejercicios cargados, revisados y publicados en un catálogo controlado por el equipo."),
         ("heading", "1. ¿Qué problema resolvemos?"), ("body", "Los PDFs contienen mucho material, pero no todo está listo para ser utilizado. Cada ejercicio puede necesitar una revisión del enunciado, del gráfico, de las unidades, de la respuesta esperada y de la forma pedagógica de acompañar al estudiante."),
         ("body", "Por eso distinguimos entre el corpus académico, que reúne todos los materiales disponibles, y el catálogo de ejercicios habilitados, que contiene únicamente los ejercicios aprobados para estudiantes."),
         ("heading", "2. Proceso para incorporar un ejercicio"),
         ("bullet", "Seleccionar: elegir un ejercicio concreto de una guía o PDF."), ("bullet", "Describir: registrar fuente, página, enunciado, gráfico y conceptos."), ("bullet", "Revisar: verificar texto, datos, unidades y límites del ejercicio."), ("bullet", "Preparar: definir qué debe acompañar el asistente y qué recursos necesita."), ("bullet", "Validar: revisar respuestas y confirmar el enfoque socrático."), ("bullet", "Publicar: habilitarlo para estudiantes únicamente después de la revisión.")],
        [("title", "Estados y ficha del ejercicio"),
         ("heading", "3. Estados de cada ejercicio"), ("body", "draft: cargado, pero todavía en preparación. validated: revisado técnica y académicamente. published: aprobado para estudiantes. archived: retirado del catálogo, conservando su registro."),
         ("heading", "4. Ficha de configuración"), ("body", "Cada ejercicio tendrá una ficha similar a esta:"),
         ("code", "id: cinematica-1d-ejercicio-02"), ("code", "status: published"), ("code", "title: Movimiento representado por una parábola"), ("code", "unit: Cinemática en 1D"), ("code", "source: Fisica1-Cuadernillo-2026.pdf, page 29"), ("code", "statement: Texto controlado del enunciado"), ("code", "concepts: position, velocity, acceleration"), ("code", "assets: cinematica-1d-ejercicio-02-x-t.svg"), ("code", "validation: revisado por el equipo de Física 1"),
         ("heading", "5. ¿Cómo interactúa el estudiante?"), ("bullet", "Ve una lista de ejercicios publicados."), ("bullet", "Selecciona un ejercicio."), ("bullet", "Recibe el enunciado y el material correspondiente."), ("bullet", "Hace preguntas dentro del contexto de ese ejercicio.")],
        [("title", "Control del alcance"),
         ("heading", "Una protección importante"), ("body", "Ocultar ejercicios en la pantalla no es suficiente. El sistema también debe verificar internamente que cada consulta tenga un ejercicio válido y recuperar únicamente la información asociada a ese ejercicio."),
         ("heading", "6. ¿Qué ocurre si pregunta por otro problema?"), ("body", "El asistente debe responder de forma clara y honesta:"), ("body", "Todavía no tengo cargado ese ejercicio. Puedo ayudarte únicamente con el ejercicio seleccionado de Cinemática en 1D."), ("body", "Esto evita que el modelo improvise una solución basada en conocimientos generales o en un ejercicio que todavía no revisamos."),
         ("heading", "7. Primer ejercicio propuesto"), ("body", "Unidad: Cinemática de la partícula en 1D. Ejercicio: número 2. Fuente: Fisica1-Cuadernillo-2026.pdf, página impresa 25 / página PDF aproximada 29. Contenido: análisis de un gráfico de posición en función del tiempo y construcción de v(t) y a(t)."), ("body", "Es un buen primer ejercicio porque tiene un gráfico identificable, objetivos concretos y permite evaluar tanto el razonamiento como las visualizaciones."),
         ("heading", "8. Criterio para sumar nuevos ejercicios"), ("bullet", "Agregar pocos ejercicios por vez."), ("bullet", "Revisar cada uno antes de publicarlo."), ("bullet", "Conservar la fuente original y la página."), ("bullet", "Definir conceptos y resultados esperados."), ("bullet", "Probar preguntas correctas, ambiguas y fuera de alcance."), ("bullet", "Publicar solo cuando la respuesta sea pedagógicamente aceptable.")],
        [("title", "Próximo paso"), ("heading", "9. Empezar con el ejercicio 2"), ("body", "Prepararemos su ficha, aislaremos su material en la base de conocimiento, validaremos la interacción y recién después lo dejaremos visible en el asistente."), ("body", "El mismo procedimiento se repetirá para cada ejercicio nuevo. Así podremos ampliar el catálogo de forma gradual, revisable y segura."), ("heading", "Resumen para el equipo"), ("bullet", "Un ejercicio no se publica automáticamente por estar presente en un PDF."), ("bullet", "Cada ejercicio tiene una ficha, un estado y una fuente verificable."), ("bullet", "El asistente trabaja dentro del ejercicio seleccionado."), ("bullet", "Las consultas fuera del catálogo reciben una respuesta de límite, no una solución inventada."), ("body", "Asistente de Física · Propuesta de incorporación progresiva de ejercicios")],
    ]

    objects: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [PAGE_KIDS] /Count COUNT >>"]
    page_ids = []
    for page in pages:
        content = line_commands(page)
        content_id = len(objects) + 1
        objects.append(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream")
        page_id = len(objects) + 1
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] /Resources << /Font << /F1 {len(objects)+1} 0 R /F2 {len(objects)+2} 0 R >> >> /Contents {content_id} 0 R >>".encode())
        objects.extend([b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"])
        page_ids.append(page_id)

    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(f'{p} 0 R' for p in page_ids)}] /Count {len(page_ids)} >>".encode()
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(output)


if __name__ == "__main__":
    make_pdf(Path("docs/guia-incorporacion-ejercicios.pdf"))
