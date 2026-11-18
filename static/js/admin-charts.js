// admin-charts.js - Gráficos del panel de administración
// Estilo combinado: DESIGN (4).md (Anthropic: Pergamino & Terracota Clay) + Factory (Geist Mono)
(function() {
    'use strict';

    const dataElement = document.getElementById('chart-data');
    if (!dataElement) {
        return;
    }

    const chartData = JSON.parse(dataElement.textContent);

    // Tipografía y tokens globales de Chart.js (Geist + Geist Mono)
    const FONT_SANS = "'Geist', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif";
    const FONT_MONO = "'Geist Mono', ui-monospace, SFMono-Regular, monospace";

    Chart.defaults.font.family = FONT_SANS;
    Chart.defaults.font.size = 12;
    Chart.defaults.color = '#6b6a65';
    Chart.defaults.plugins.legend.display = false;

    // Tooltip flotante estilo editorial (#141413 Slate Dark con texto #faf9f5 Ivory Light)
    const modernTooltip = {
        backgroundColor: '#141413',
        titleColor: '#faf9f5',
        bodyColor: '#e3dacc',
        borderColor: 'rgba(250, 249, 245, 0.14)',
        borderWidth: 1,
        cornerRadius: 12,
        padding: 10,
        displayColors: true,
        boxWidth: 8,
        boxHeight: 8,
        usePointStyle: true,
        titleFont: { family: FONT_SANS, size: 12, weight: '600' },
        bodyFont: { family: FONT_MONO, size: 12, weight: '400' }
    };

    // 1. Gráfico: Top 10 Libros Más Rentados (#1 destacado en Terracotta Clay #d97757, resto Slate Dark #141413)
    const chartLibrosElement = document.getElementById('chartLibrosTop');
    if (chartLibrosElement && chartData.topLibros) {
        const count = (chartData.topLibros.data || []).length;
        const barColors = Array.from({ length: count }, (_, i) => i === 0 ? '#d97757' : '#141413');
        const hoverColors = Array.from({ length: count }, (_, i) => i === 0 ? '#c6613f' : '#30302e');

        new Chart(chartLibrosElement, {
            type: 'bar',
            data: {
                labels: chartData.topLibros.labels,
                datasets: [{
                    label: 'Rentas',
                    data: chartData.topLibros.data,
                    backgroundColor: barColors,
                    hoverBackgroundColor: hoverColors,
                    borderRadius: 6,
                    borderSkipped: false,
                    barThickness: 18
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: modernTooltip
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        border: { display: false },
                        grid: { color: '#d8d6ce', tickBorderDash: [4, 4] },
                        ticks: { precision: 0, font: { family: FONT_MONO, size: 11 }, color: '#6b6a65' }
                    },
                    y: {
                        border: { display: false },
                        grid: { display: false },
                        ticks: { autoSkip: false, font: { family: FONT_SANS, size: 12, weight: '500' }, color: '#141413' }
                    }
                }
            }
        });
    }

    // 2. Gráfico: Top 10 Usuarios Activos (#1 en Emerald #059669, resto Graphite Warm #4d4c48)
    const chartUsuariosElement = document.getElementById('chartUsuariosTop');
    if (chartUsuariosElement && chartData.topUsuarios) {
        const count = (chartData.topUsuarios.data || []).length;
        const barColors = Array.from({ length: count }, (_, i) => i === 0 ? '#059669' : '#4d4c48');
        const hoverColors = Array.from({ length: count }, (_, i) => i === 0 ? '#047857' : '#30302e');

        new Chart(chartUsuariosElement, {
            type: 'bar',
            data: {
                labels: chartData.topUsuarios.labels,
                datasets: [{
                    label: 'Préstamos',
                    data: chartData.topUsuarios.data,
                    backgroundColor: barColors,
                    hoverBackgroundColor: hoverColors,
                    borderRadius: 6,
                    borderSkipped: false,
                    barThickness: 18
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: modernTooltip
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        border: { display: false },
                        grid: { color: '#d8d6ce' },
                        ticks: { precision: 0, font: { family: FONT_MONO, size: 11 }, color: '#6b6a65' }
                    },
                    y: {
                        border: { display: false },
                        grid: { display: false },
                        ticks: { autoSkip: false, font: { family: FONT_SANS, size: 12, weight: '500' }, color: '#141413' }
                    }
                }
            }
        });
    }

    // 3. Gráfico: Tendencia de Préstamos (Área con degradado Terracotta Clay + línea Slate Dark)
    const chartTendenciaElement = document.getElementById('chartTendencia');
    if (chartTendenciaElement && chartData.tendencia) {
        const ctx = chartTendenciaElement.getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 250);
        gradient.addColorStop(0, 'rgba(217, 119, 87, 0.24)');
        gradient.addColorStop(1, 'rgba(217, 119, 87, 0.00)');

        new Chart(chartTendenciaElement, {
            type: 'line',
            data: {
                labels: chartData.tendencia.labels,
                datasets: [{
                    label: 'Préstamos del día',
                    data: chartData.tendencia.data,
                    borderColor: '#141413',
                    borderWidth: 2,
                    backgroundColor: gradient,
                    pointBackgroundColor: '#d97757',
                    pointBorderColor: '#faf9f5',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    tension: 0.35,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    tooltip: modernTooltip
                },
                scales: {
                    x: {
                        border: { display: false },
                        grid: { display: false },
                        ticks: { font: { family: FONT_MONO, size: 11 }, color: '#6b6a65' }
                    },
                    y: {
                        beginAtZero: true,
                        border: { display: false },
                        grid: { color: '#d8d6ce' },
                        ticks: { precision: 0, font: { family: FONT_MONO, size: 11 }, color: '#6b6a65' }
                    }
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
