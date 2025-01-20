// app/static/js/measurement-handlers.js

document.addEventListener('DOMContentLoaded', function() {
    // Initialize chart
    let measurementChart = null;
    const chartCtx = document.getElementById('progressChart');
    
    if (chartCtx) {
        measurementChart = new Chart(chartCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Progress',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: false
                    }
                },
                plugins: {
                    legend: {
                        onClick: null // Disable legend click
                    }
                }
            }
        });
    }

    // Handle range selection
    const rangeSelector = document.getElementById('timeRange');
    if (rangeSelector) {
        rangeSelector.addEventListener('change', function() {
            updateChart(this.value);
        });
    }

    // Handle unit toggle
    const unitToggle = document.getElementById('unitToggle');
    if (unitToggle) {
        unitToggle.addEventListener('change', function() {
            const currentValue = document.getElementById('measurementValue').value;
            if (currentValue) {
                // Convert value based on selected unit
                if (this.value === 'in') {
                    document.getElementById('measurementValue').value = (parseFloat(currentValue) * 0.393701).toFixed(1);
                } else {
                    document.getElementById('measurementValue').value = (parseFloat(currentValue) / 0.393701).toFixed(1);
                }
            }
            updateChart(rangeSelector.value);
        });
    }

    // Function to update chart
    function updateChart(range) {
        const measurementType = document.getElementById('measurementType').value;
        const unit = unitToggle ? unitToggle.value : document.getElementById('defaultUnit').value;
        
        fetch(`/api/measurement-data/${measurementType}?range=${range}`)
            .then(response => response.json())
            .then(data => {
                if (data.values.length === 0) {
                    // Show no data message
                    document.getElementById('noDataMessage').style.display = 'block';
                    document.getElementById('progressChart').style.display = 'none';
                    return;
                }

                // Hide no data message and show chart
                document.getElementById('noDataMessage').style.display = 'none';
                document.getElementById('progressChart').style.display = 'block';

                // Convert values if necessary
                let displayValues = data.values;
                if (unit === 'in') {
                    displayValues = data.values.map(v => v * 0.393701);
                }

                // Update chart
                measurementChart.data.labels = data.labels;
                measurementChart.data.datasets[0].data = displayValues;
                measurementChart.options.scales.y.title = {
                    display: true,
                    text: unit
                };
                measurementChart.update();
            })
            .catch(error => console.error('Error fetching measurement data:', error));
    }

    // Load measurement diary
    const diaryDate = document.getElementById('diaryDate');
    if (diaryDate) {
        diaryDate.addEventListener('change', function() {
            fetch(`/api/measurements-diary/${this.value}`)
                .then(response => response.json())
                .then(data => {
                    const diaryContent = document.getElementById('diaryContent');
                    if (data.measurements.length === 0) {
                        diaryContent.innerHTML = '<p>No measurements recorded for this date.</p>';
                        return;
                    }

                    let html = '<table class="w-full"><thead><tr><th>Measurement</th><th>Value</th><th>Unit</th></tr></thead><tbody>';
                    data.measurements.forEach(m => {
                        html += `<tr>
                            <td>${m.type.replace('_', ' ').charAt(0).toUpperCase() + m.type.slice(1)}</td>
                            <td>${m.value}</td>
                            <td>${m.unit}</td>
                        </tr>`;
                    });
                    html += '</tbody></table>';
                    diaryContent.innerHTML = html;
                })
                .catch(error => console.error('Error fetching diary data:', error));
        });
    }

    // Initial chart load if we're on the tracking page
    if (chartCtx && rangeSelector) {
        updateChart(rangeSelector.value);
    }
});