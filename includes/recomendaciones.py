import json
import math
import re
from collections import Counter

class SistemaRecomendacion:
    def __init__(self, prestamos_usuario, todos_libros):
        self.prestamos_usuario = prestamos_usuario
        self.todos_libros = todos_libros

    def _calcular_similitud_content(self, libro, perfil):
        # Ponderaciones: genero (0.4), autor (0.3), tags (0.3)
        score = 0.0
        
        # Genero
        if libro.genero and perfil['generos']:
            gen = libro.genero.strip().lower()
            if gen in perfil['generos']:
                score += 0.4 * (perfil['generos'][gen] / perfil['total_prestamos'])
                
        # Autor
        if libro.autor and perfil['autores']:
            aut = libro.autor.strip().lower()
            if aut in perfil['autores']:
                score += 0.3 * (perfil['autores'][aut] / perfil['total_prestamos'])
                
        # Tags - Jaccard similarity o interseccion simple ponderada
        if libro.tags and perfil['tags']:
            tags_libro = set([t.strip().lower() for t in libro.tags.split(',')])
            interseccion = 0
            for tag in tags_libro:
                if tag in perfil['tags']:
                    interseccion += perfil['tags'][tag]
            if interseccion > 0:
                score += 0.3 * (interseccion / (len(tags_libro) * perfil['total_prestamos']))
                
        # Refuerzo por ultimo libro
        ultimo_libro = perfil['ultimo_libro']
        if ultimo_libro:
            if libro.genero == ultimo_libro.genero:
                score += 0.1
            if libro.autor == ultimo_libro.autor:
                score += 0.1
                
        return score

    def generar_recomendaciones(self, limite=3):
        if not self.prestamos_usuario:
            return []

        # Construir perfil del usuario
        perfil = {
            'generos': Counter(),
            'autores': Counter(),
            'tags': Counter(),
            'total_prestamos': len(self.prestamos_usuario),
            'ultimo_libro': self.prestamos_usuario[-1] if self.prestamos_usuario else None
        }
        
        borrowed_ids = set()
        for libro in self.prestamos_usuario:
            borrowed_ids.add(libro.id)
            if libro.genero:
                perfil['generos'][libro.genero.strip().lower()] += 1
            if libro.autor:
                perfil['autores'][libro.autor.strip().lower()] += 1
            if libro.tags:
                for tag in libro.tags.split(','):
                    perfil['tags'][tag.strip().lower()] += 1
                    
        candidatos = [l for l in self.todos_libros if l.id not in borrowed_ids and l.activo]
        
        if not candidatos:
            return []
            
        # Matriz de decision (Filas=candidatos, Columnas=[Similitud, Popularidad, Disponibilidad])
        matrix = []
        for l in candidatos:
            sim = self._calcular_similitud_content(l, perfil)
            pop = float(l.veces_rentado or 0)
            disp = float(l.disponibles or 0)
            matrix.append([sim, pop, disp])

        # SAW: normalizar con máximos y aplicar pesos (similitud 0.5, popularidad 0.3, disponibilidad 0.2)
        pesos = {"sim": 0.5, "pop": 0.3, "disp": 0.2}
        max_sim = max((row[0] for row in matrix), default=0) or 1
        max_pop = max((row[1] for row in matrix), default=0) or 1
        max_disp = max((row[2] for row in matrix), default=0) or 1

        scores = []
        for idx, libro in enumerate(candidatos):
            sim_norm = matrix[idx][0] / max_sim
            pop_norm = math.sqrt(matrix[idx][1]) / math.sqrt(max_pop)
            disp_norm = math.sqrt(matrix[idx][2]) / math.sqrt(max_disp)
            score = round(
                (sim_norm * pesos["sim"]) + (pop_norm * pesos["pop"]) + (disp_norm * pesos["disp"]),
                4,
            )
            scores.append((libro, round(score * 100, 2)))

        # Ajuste de porcentaje por autor + genero para evitar saltos bruscos
        grupo_promedio = {}
        grupo_count = {}
        for libro, sc in scores:
            autor_key = (libro.autor or "").strip().lower()
            genero_key = (libro.genero or "").strip().lower()
            key = (autor_key, genero_key)
            grupo_promedio[key] = grupo_promedio.get(key, 0.0) + sc
            grupo_count[key] = grupo_count.get(key, 0) + 1

        for key in list(grupo_promedio.keys()):
            if grupo_count[key]:
                grupo_promedio[key] = round(grupo_promedio[key] / grupo_count[key], 2)

        scores_ajustados = []
        for libro, sc in scores:
            autor_key = (libro.autor or "").strip().lower()
            genero_key = (libro.genero or "").strip().lower()
            key = (autor_key, genero_key)
            promedio = grupo_promedio.get(key, sc)
            sc_ajustado = round((sc * 0.6) + (promedio * 0.4), 2)
            scores_ajustados.append((libro, sc_ajustado))

        # Agrupar ediciones similares (mismo titulo base + autor)
        def _titulo_base(titulo):
            base = (titulo or "").strip().lower()
            base = re.sub(r"\(.*?\)", "", base)
            base = re.sub(r"\s+-\s+.*$", "", base)
            base = re.sub(r"\s+", " ", base)
            return base.strip()

        agrupados = {}
        for libro, sc in scores_ajustados:
            base = _titulo_base(libro.titulo)
            autor_key = (libro.autor or "").strip().lower()
            key = (base, autor_key)
            if key not in agrupados or sc > agrupados[key][1]:
                agrupados[key] = (libro, sc)

        scores = list(agrupados.values())

        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Lógica de Diversificación (2 del género más popular + 1 nuevo género)
        genero_principal = None
        if perfil['generos']:
            top_genero = perfil['generos'].most_common(1)[0]
            if top_genero[1] >= 2:
                genero_principal = top_genero[0]

        resultado = []
        if genero_principal and limite >= 3:
            mismo_genero = []
            distinto_genero = []
            
            for l, sc in scores:
                gen_libro = (l.genero or "").strip().lower()
                if gen_libro == genero_principal and len(mismo_genero) < 2:
                    mismo_genero.append((l, sc))
                elif gen_libro != genero_principal and len(distinto_genero) < 1:
                    distinto_genero.append((l, sc))
            
            if len(mismo_genero) == 2 and len(distinto_genero) >= 1:
                # 2 del mismo género
                for l, sc in mismo_genero:
                    resultado.append({
                        "libro_id": l.id,
                        "titulo": l.titulo,
                        "autor": l.autor,
                        "genero": l.genero,
                        "score": sc,
                        "razon": f"Coincide con tu gusto principal por el género {l.genero}"
                    })
                # 1 diferente para ampliar gustos
                for l, sc in distinto_genero:
                    resultado.append({
                        "libro_id": l.id,
                        "titulo": l.titulo,
                        "autor": l.autor,
                        "genero": l.genero,
                        "score": sc,
                        "razon": "Para ampliar tus gustos, una excelente opción de un género distinto"
                    })
                return resultado
                
        # Fallback si no cumple reglas de diversificación (ej. menos de 2 rentas de un género)
        top = scores[:limite]
        for l, sc in top:
            resultado.append({
                "libro_id": l.id,
                "titulo": l.titulo,
                "autor": l.autor,
                "genero": l.genero,
                "score": sc,
                "razon": "Te lo recomendamos basado en tus préstamos recientes"
            })

        return resultado
