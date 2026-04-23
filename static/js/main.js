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
function mostrarMensaje(mensaje, tipo = 'success') {
    const alertClass = {
        'success': 'alert-success-custom',
        'error': 'alert-danger-custom',
        'warning': 'alert-warning-custom',
        'info': 'alert-info-custom'
    }[tipo] || 'alert-info-custom';
    const alert = document.createElement('div');
    alert.className = `alert ${alertClass} alert-custom fade-in`;
    alert.innerHTML = `
        <i class="bi bi-check-circle-fill me-2"></i>
        ${mensaje}
    `;
    document.body.insertAdjacentElement('afterbegin', alert);
    setTimeout(() => {
        alert.remove();
    }, 3000);
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
        const filas = tabla.querySelectorAll('tbody tr');
        const columnaFiltro = select ? select.value : 'todas';
        
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
            
            fila.style.display = texto.includes(filtro) ? '' : 'none';
        });
    }
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
