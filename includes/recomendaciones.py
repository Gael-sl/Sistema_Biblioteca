import json
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

    def generar_recomendaciones(self, limite=5):
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

        # SAW: normalizar con máximos y aplicar pesos (similitud 0.7, popularidad 0.1, disponibilidad 0.2)
        pesos = {"sim": 0.7, "pop": 0.1, "disp": 0.2}
        max_sim = max((row[0] for row in matrix), default=0) or 1
        max_pop = max((row[1] for row in matrix), default=0) or 1
        max_disp = max((row[2] for row in matrix), default=0) or 1

        scores = []
        for idx, libro in enumerate(candidatos):
            sim_norm = matrix[idx][0] / max_sim
            pop_norm = matrix[idx][1] / max_pop
            disp_norm = matrix[idx][2] / max_disp
            score = round(
                (sim_norm * pesos["sim"]) + (pop_norm * pesos["pop"]) + (disp_norm * pesos["disp"]),
                4,
            )
            scores.append((libro, round(score * 100, 2)))

        scores.sort(key=lambda x: x[1], reverse=True)
        top = scores[:limite]

        resultado = []
        for l, sc in top:
            resultado.append({
                "libro_id": l.id,
                "titulo": l.titulo,
                "autor": l.autor,
                "genero": l.genero,
                "score": sc
            })

        return resultado
