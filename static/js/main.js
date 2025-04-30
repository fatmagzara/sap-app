// All JavaScript content from the script tag in index.html
document.addEventListener('DOMContentLoaded', function() {
    const socket = io({
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: 5,
        timeout: 20000
    });

    const statusIndicator = document.getElementById('connection-status');
    const testButtons = document.querySelectorAll('.test-btn');
    const resultCells = document.querySelectorAll('[id^="result_"]');
    const certificationTicket = document.getElementById('certification-ticket');
    const historyModal = document.getElementById('history-modal');

    let testResults = {
        'Bobine': '⏳ En attente...',
        'Lames': '⏳ En attente...',
        'Capteurs': '⏳ En attente...'
    };
    let testHistory = [];
    let isConnected = false;

    function updateConnectionStatus(status) {
        if (status.includes('Connecté')) {
            statusIndicator.textContent = '🟢 Raspberry Pi Connecté';
            statusIndicator.className = 'status-indicator status-connected';
            updateButtonsState(true);
            isConnected = true;
        } else {
            statusIndicator.textContent = '🔴 Raspberry Pi Déconnecté';
            statusIndicator.className = 'status-indicator status-disconnected';
            updateButtonsState(false);
            isConnected = false;
        }
    }

    function updateButtonsState(enabled) {
        testButtons.forEach(button => {
            if (!button.classList.contains('running')) {
                button.disabled = !enabled;
                button.style.cursor = enabled ? 'pointer' : 'not-allowed';
            }
        });
    }

    function updateResultStyle(element, result) {
        element.textContent = result;
        element.className = 'result-cell';

        if (result.includes('En attente')) {
            element.classList.add('result-pending');
        } else if (result.includes('Test en cours')) {
            element.classList.add('result-running');
        } else if (result.includes('✅') || result.includes('OK') || result.includes('Réussi')) {
            element.classList.add('result-success');
        } else if (result.includes('❌') || result.includes('Échec') || result.includes('Erreur')) {
            element.classList.add('result-error');
        }
    }

    resultCells.forEach(cell => {
        const type = cell.id.split('_')[1];
        updateResultStyle(cell, testResults[type] || '⏳ En attente...');
    });

    socket.on('connect', function() {
        console.log('Connected to server');
        socket.emit('request_status');
    });

    socket.on('disconnect', function() {
        if (isConnected) {
            updateConnectionStatus('Déconnecté');
        }
    });

    socket.on('update_connection_status', function(data) {
        updateConnectionStatus(data.status);
    });

    window.startTest = function(type, buttonElement) {
        if (!isConnected) return;

        buttonElement.disabled = true;
        buttonElement.textContent = "Test en cours...";
        buttonElement.classList.add('running');

        const resultCell = document.getElementById(`result_${type}`);
        updateResultStyle(resultCell, "Test en cours...");

        socket.emit('start_test', { type: type });
        testResults[type] = 'Test en cours...';
    };

    socket.on('update_result', function(data) {
        const type = data.type;
        const result = data.result;

        testResults[type] = result;

        const resultCell = document.getElementById(`result_${type}`);
        if (resultCell) {
            updateResultStyle(resultCell, result);
        }

        const buttons = document.querySelectorAll('.test-btn');
        buttons.forEach(button => {
            if (button.onclick && button.onclick.toString().includes(type)) {
                button.disabled = !isConnected;
                button.textContent = "Lancer Test";
                button.classList.remove('running');
            }
        });

        if (isCompletedResult(result)) {
            const now = new Date();
            testHistory.push({
                date: now.toLocaleString(),
                test: type,
                result: result
            });
        }

        if (certificationTicket.classList.contains("show")) {
            document.getElementById(`ticket_${type}`).textContent = `Test ${type}: ${result}`;
        }
    });

    function isCompletedResult(result) {
        return !result.includes('En attente') && !result.includes('Test en cours');
    }

    window.generateCertificationTicket = function() {
        certificationTicket.classList.add('show');
        document.getElementById('ticket_Bobine').textContent = `Test Bobine: ${testResults.Bobine}`;
        document.getElementById('ticket_Lames').textContent = `Test des Lames: ${testResults.Lames}`;
        document.getElementById('ticket_Capteurs').textContent = `Test des Capteurs: ${testResults.Capteurs}`;
        document.getElementById('ticket-date').textContent = new Date().toLocaleString();
    };

    window.printTicket = function() {
        window.print();
    };

    window.showHistory = function() {
        const historyTbody = document.getElementById('history-tbody');
        historyTbody.innerHTML = '';

        const completedTests = testHistory.filter(entry => isCompletedResult(entry.result));

        if (completedTests.length > 0) {
            completedTests.slice(-5).forEach(entry => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${entry.date}</td>
                    <td>${entry.test}</td>
                    <td>${entry.result}</td>
                `;
                historyTbody.appendChild(row);
            });
        } else {
            const row = document.createElement('tr');
            row.innerHTML = `<td colspan="3" style="text-align: center;">Aucun historique disponible</td>`;
            historyTbody.appendChild(row);
        }

        historyModal.style.display = 'block';
        setTimeout(() => {
            historyModal.classList.add('show');
        }, 10);
    };

    window.closeHistory = function() {
        historyModal.classList.remove('show');
        setTimeout(() => {
            historyModal.style.display = 'none';
        }, 300);
    };

    window.logout = function() {
        window.location.href = '/logout';
    };

    updateButtonsState(false);
});