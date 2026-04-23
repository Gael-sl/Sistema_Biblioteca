// admin-charts.js - Gráficos del panel de administración
(function() {
    'use strict';
    
    // Obtener datos del DOM
    const dataElement = document.getElementById('chart-data');
    if (!dataElement) {
        console.error('No se encontraron datos para los gráficos');
        return;
    }
    
    const chartData = JSON.parse(dataElement.textContent);
    
    // Configuración global de Chart.js
    Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    Chart.defaults.plugins.legend.display = false;
    
    // Gráfico: Top 10 Libros Más Rentados
    const chartLibrosElement = document.getElementById('chartLibrosTop');
    if (chartLibrosElement && chartData.topLibros) {
        new Chart(chartLibrosElement, {
            type: 'bar',
            data: {
                labels: chartData.topLibros.labels,
                datasets: [{
                    data: chartData.topLibros.data,
                    backgroundColor: '#007AFF',
                    borderRadius: 8,
                    barThickness: 20
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { beginAtZero: true, ticks: { precision: 0 } },
                    y: { ticks: { autoSkip: false } }
                }
            }
        });
    }
    
    // Gráfico: Top 10 Usuarios Activos
    const chartUsuariosElement = document.getElementById('chartUsuariosTop');
    if (chartUsuariosElement && chartData.topUsuarios) {
        new Chart(chartUsuariosElement, {
            type: 'bar',
            data: {
                labels: chartData.topUsuarios.labels,
                datasets: [{
                    data: chartData.topUsuarios.data,
                    backgroundColor: '#34c759',
                    borderRadius: 8,
                    barThickness: 20
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { beginAtZero: true, ticks: { precision: 0 } },
                    y: { ticks: { autoSkip: false } }
                }
            }
        });
    }
    
    // Gráfico: Tendencia de Préstamos
    const chartTendenciaElement = document.getElementById('chartTendencia');
    if (chartTendenciaElement && chartData.tendencia) {
        new Chart(chartTendenciaElement, {
            type: 'line',
            data: {
                labels: chartData.tendencia.labels,
                datasets: [{
                    label: 'Préstamos',
                    data: chartData.tendencia.data,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } }
                }
            }
        });
    }
    
    // Modal editar usuario del sistema
    const modalElement = document.getElementById('modalEditarUsuarioSistema');
    if (modalElement) {
        modalElement.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const id = button.getAttribute('data-id');
            const username = button.getAttribute('data-username');
            const role = button.getAttribute('data-role');
            
            document.getElementById('edit_sys_username').value = username;
            document.getElementById('edit_sys_role').value = role;
            document.getElementById('formEditarUsuarioSistema').action = `/admin/usuarios/${id}/editar`;
        });
    }
})();
