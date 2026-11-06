function showAlert(message, title = 'Aviso', type = 'info', onConfirm = null) {
    const modalEl = document.getElementById('glassAlertModal');
    if (!modalEl) return;
    const modal = new bootstrap.Modal(modalEl);
    
    document.getElementById('glassAlertTitle').textContent = title;
    document.getElementById('glassAlertMessage').textContent = message;
    
    const iconContainer = document.getElementById('glassAlertIcon');
    const iconInner = document.getElementById('glassAlertIconInner');
    const btnConfirm = document.getElementById('glassAlertBtnConfirm');
    const btnCancel = document.getElementById('glassAlertBtnCancel');
    
    btnCancel.classList.add('d-none');
    btnConfirm.textContent = 'Entendido';
    
    if (type === 'success') {
        iconContainer.style.background = 'rgba(16, 185, 129, 0.1)';
        iconInner.className = 'bi bi-check-circle text-success';
        btnConfirm.style.background = 'linear-gradient(135deg, #10b981, #059669)';
        btnConfirm.style.boxShadow = '0 4px 15px rgba(16, 185, 129, 0.3)';
    } else if (type === 'error') {
        iconContainer.style.background = 'rgba(239, 68, 68, 0.1)';
        iconInner.className = 'bi bi-x-circle text-danger';
        btnConfirm.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
        btnConfirm.style.boxShadow = '0 4px 15px rgba(239, 68, 68, 0.3)';
    } else if (type === 'warning') {
        iconContainer.style.background = 'rgba(245, 158, 11, 0.1)';
        iconInner.className = 'bi bi-exclamation-circle text-warning';
        btnConfirm.style.background = 'linear-gradient(135deg, #f59e0b, #d97706)';
        btnConfirm.style.boxShadow = '0 4px 15px rgba(245, 158, 11, 0.3)';
    } else {
        iconContainer.style.background = 'rgba(59, 130, 246, 0.1)';
        iconInner.className = 'bi bi-info-circle text-primary';
        btnConfirm.style.background = 'linear-gradient(135deg, #3b82f6, #2563eb)';
        btnConfirm.style.boxShadow = '0 4px 15px rgba(59, 130, 246, 0.3)';
    }
    
    // Eliminar listeners previos
    const newBtnConfirm = btnConfirm.cloneNode(true);
    btnConfirm.parentNode.replaceChild(newBtnConfirm, btnConfirm);
    
    newBtnConfirm.addEventListener('click', () => {
        modal.hide();
        if (onConfirm) onConfirm();
    });
    
    modal.show();
}

function showConfirm(message, title = 'Confirmar', onConfirm) {
    const modalEl = document.getElementById('glassAlertModal');
    if (!modalEl) return;
    const modal = new bootstrap.Modal(modalEl);
    
    document.getElementById('glassAlertTitle').textContent = title;
    document.getElementById('glassAlertMessage').textContent = message;
    
    const iconContainer = document.getElementById('glassAlertIcon');
    const iconInner = document.getElementById('glassAlertIconInner');
    const btnConfirm = document.getElementById('glassAlertBtnConfirm');
    const btnCancel = document.getElementById('glassAlertBtnCancel');
    
    btnCancel.classList.remove('d-none');
    btnConfirm.textContent = 'Confirmar';
    
    iconContainer.style.background = 'rgba(245, 158, 11, 0.1)';
    iconInner.className = 'bi bi-question-circle text-warning';
    
    btnConfirm.style.background = 'linear-gradient(135deg, #3b82f6, #2563eb)';
    btnConfirm.style.boxShadow = '0 4px 15px rgba(59, 130, 246, 0.3)';
    
    // Eliminar listeners previos
    const newBtnConfirm = btnConfirm.cloneNode(true);
    btnConfirm.parentNode.replaceChild(newBtnConfirm, btnConfirm);
    
    newBtnConfirm.addEventListener('click', () => {
        modal.hide();
        if (onConfirm) onConfirm();
    });
    
    modal.show();
}

function confirmarEliminacion(mensaje) {
    // Deprecated for direct calls, returning false stops form submission
    return false; // Will need custom event handling for forms
}
function validarFormulario(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        return false;
    }
    return true;
}
/**
 * Escapa texto para insertarlo de forma segura dentro de innerHTML / plantillas.
 * Evita XSS cuando se pintan datos capturados por usuarios (nombres, observaciones, títulos).
 */
function escapeHtml(valor) {
    return String(valor ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function mostrarMensaje(mensaje, tipo = 'success') {
    mensaje = escapeHtml(mensaje);
    const iconClass = {
        'success': 'bi-check-circle-fill',
        'error': 'bi-x-circle-fill',
        'warning': 'bi-exclamation-circle-fill',
        'info': 'bi-info-circle-fill'
    }[tipo] || 'bi-info-circle-fill';
    
    const colorBg = {
        'success': 'rgba(16, 185, 129, 0.95)',
        'error': 'rgba(239, 68, 68, 0.95)',
        'warning': 'rgba(245, 158, 11, 0.95)',
        'info': 'rgba(59, 130, 246, 0.95)'
    }[tipo] || 'rgba(59, 130, 246, 0.95)';
    
    const alert = document.createElement('div');
    alert.className = 'toast-notification';
    alert.style.cssText = `
        position: fixed;
        bottom: 30px;
        right: 30px;
        background: ${colorBg};
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(10px);
        z-index: 9999;
        animation: slideInRight 0.3s ease-out, slideOutRight 0.3s ease-out 4.7s forwards;
    `;
    alert.innerHTML = `
        <i class="bi ${iconClass}" style="font-size: 18px; flex-shrink: 0;"></i>
        <span>${mensaje}</span>
    `;
    
    // Agregar estilos de animación si no existen
    if (!document.getElementById('toastStyles')) {
        const style = document.createElement('style');
        style.id = 'toastStyles';
        style.textContent = `
            @keyframes slideInRight {
                from {
                    transform: translateX(400px);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            @keyframes slideOutRight {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(400px);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(alert);
    setTimeout(() => {
        alert.remove();
    }, 5000);
}
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});
function buscarEnTabla(inputId, tablaId, selectColumnaId = null) {
    const input = document.getElementById(inputId);
    const tabla = document.getElementById(tablaId);
    const select = selectColumnaId ? document.getElementById(selectColumnaId) : null;
    if (!input || !tabla) return;
    
    input.addEventListener('keyup', function() {
        filtrarTabla();
    });
    
    if (select) {
        select.addEventListener('change', filtrarTabla);
    }
    
    function filtrarTabla() {
        const filtro = input.value.toLowerCase();
        const filas = Array.from(tabla.querySelectorAll('tbody tr'));
        const columnaFiltro = select ? select.value : 'todas';
        
        let visibles = 0;
        filas.forEach(fila => {
            const celdas = fila.querySelectorAll('td');
            let texto = '';
            
            if (columnaFiltro === 'todas') {
                texto = fila.textContent.toLowerCase();
            } else {
                const indice = parseInt(columnaFiltro);
                if (celdas[indice]) {
                    texto = celdas[indice].textContent.toLowerCase();
                }
            }
            
            const match = texto.includes(filtro);
            if (match) {
                fila.classList.remove('filtro-oculto');
                visibles++;
            } else {
                fila.classList.add('filtro-oculto');
                fila.style.display = 'none';
            }
        });

        // Si la tabla tiene paginación activa, reiniciarla a la página 1
        if (tabla.dataset.paginacionActiva === 'true') {
            tabla.dataset.paginaActual = '1';
            window.actualizarPaginacion(tablaId);
        } else {
            // Si no hay paginación, solo mostrar los que hacen match
            filas.forEach(f => {
                if (!f.classList.contains('filtro-oculto')) f.style.display = '';
            });
        }
    }
}

/**
 * 2.4 — Paginación dinámica para tablas (estética Liquid Glass)
 */
function paginarTabla(tablaId, filasPorPagina = 8) {
    const tabla = document.getElementById(tablaId);
    if (!tabla) return;

    tabla.dataset.paginacionActiva = 'true';
    tabla.dataset.filasPorPagina = filasPorPagina;
    tabla.dataset.paginaActual = '1';

    // Crear contenedor de controles si no existe
    let controles = document.getElementById(tablaId + '-paginacion');
    if (!controles) {
        controles = document.createElement('div');
        controles.id = tablaId + '-paginacion';
        controles.className = 'd-flex justify-content-center align-items-center gap-3 mt-4 fade-in';
        tabla.parentNode.insertBefore(controles, tabla.nextSibling);
    }

    window.actualizarPaginacion = function(id) {
        const t = document.getElementById(id);
        const c = document.getElementById(id + '-paginacion');
        const rows = Array.from(t.querySelectorAll('tbody tr')).filter(r => !r.classList.contains('filtro-oculto'));
        const total = rows.length;
        const perPage = parseInt(t.dataset.filasPorPagina);
        const totalPages = Math.max(1, Math.ceil(total / perPage));
        let current = parseInt(t.dataset.paginaActual);

        if (current > totalPages) current = totalPages;
        t.dataset.paginaActual = current;

        // Ocultar todos primero
        t.querySelectorAll('tbody tr').forEach(r => r.style.display = 'none');

        // Mostrar solo los de la página actual
        const start = (current - 1) * perPage;
        const end = start + perPage;
        rows.slice(start, end).forEach(r => r.style.display = '');

        // Actualizar controles con estilo glass
        c.innerHTML = `
            <button class="btn btn-light-custom p-0 d-flex align-items-center justify-content-center" 
                style="width: 36px; height: 36px; border-radius: 10px;" 
                onclick="cambiarPagina('${id}', ${current - 1})" ${current === 1 ? 'disabled opacity-50' : ''}>
                <i class="bi bi-chevron-left"></i>
            </button>
            <span class="text-sm fw-bold px-3 py-1 rounded-pill" style="background: rgba(0,0,0,0.05); color: #1d1d1f;">
                Página ${current} de ${totalPages}
            </span>
            <button class="btn btn-light-custom p-0 d-flex align-items-center justify-content-center" 
                style="width: 36px; height: 36px; border-radius: 10px;" 
                onclick="cambiarPagina('${id}', ${current + 1})" ${current === totalPages ? 'disabled opacity-50' : ''}>
                <i class="bi bi-chevron-right"></i>
            </button>
        `;
    };

    window.cambiarPagina = function(id, nueva) {
        const t = document.getElementById(id);
        t.dataset.paginaActual = nueva;
        window.actualizarPaginacion(id);
        // Scroll suave al inicio de la tabla
        t.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    };

    window.actualizarPaginacion(tablaId);
}

function generarQR(texto, elementoId) {
    const elemento = document.getElementById(elementoId);
    if (!elemento) return;
    elemento.innerHTML = '';
    new QRCode(elemento, {
        text: texto,
        width: 200,
        height: 200,
        colorDark: "#000000",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.H
    });
}
function imprimirElemento(elementoId) {
    const elemento = document.getElementById(elementoId);
    if (!elemento) return;
    const ventana = window.open('', '', 'height=600,width=800');
    ventana.document.write('<html><head><title>Imprimir</title>');
    ventana.document.write('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">');
    ventana.document.write('<link href="../css/biblioteca.css" rel="stylesheet">');
    ventana.document.write('</head><body>');
    ventana.document.write(elemento.innerHTML);
    ventana.document.write('</body></html>');
    ventana.document.close();
    ventana.print();
}
function formatearFecha(fecha) {
    const d = new Date(fecha);
    const dia = String(d.getDate()).padStart(2, '0');
    const mes = String(d.getMonth() + 1).padStart(2, '0');
    const anio = d.getFullYear();
    return `${dia}/${mes}/${anio}`;
}
function calcularDiasEntreFechas(fecha1, fecha2) {
    const d1 = new Date(fecha1);
    const d2 = new Date(fecha2);
    const diff = Math.abs(d2 - d1);
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
}
