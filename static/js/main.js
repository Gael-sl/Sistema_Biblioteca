function confirmarEliminacion(mensaje) {
    return confirm(mensaje || '¿Estás seguro de realizar esta acción?');
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
