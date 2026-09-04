// static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
    // Tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-dismiss alerts
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.classList.add('fade');
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });

    // Filtros - auto-submit en selects
    const filterSelects = document.querySelectorAll('.filter-select');
    filterSelects.forEach(select => {
        select.addEventListener('change', function() {
            this.closest('form').submit();
        });
    });

    // Validación de fechas
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        input.addEventListener('change', function() {
            const startDate = document.getElementById('start_date');
            const endDate = document.getElementById('end_date');
            const exactDate = document.getElementById('date');
            
            // Si se selecciona fecha exacta, limpiar rango
            if (this.id === 'date' && this.value) {
                if (startDate) startDate.value = '';
                if (endDate) endDate.value = '';
            }
            
            // Si se selecciona rango, limpiar fecha exacta
            if ((this.id === 'start_date' || this.id === 'end_date') && this.value) {
                if (exactDate) exactDate.value = '';
            }
        });
    });

    // Función para exportar datos (para futuras implementaciones)
    window.exportData = function(format = 'json') {
        const url = window.location.pathname + '?export=true&format=' + format;
        window.location.href = url;
    };

    // Función para imprimir
    window.printTable = function() {
        window.print();
    };

    console.log('Bet Models Dashboard cargado correctamente');
});