document.addEventListener('DOMContentLoaded', () => {
    // Estado
    let connections = [];
    let selectedOrigenId = null;
    let selectedTables = new Set();
    let currentTaskId = null;
    let pollInterval = null;

    // DOM Elements
    const treeContainer = document.getElementById('tree-container');
    const destSelect = document.getElementById('dest-select');
    const lblOrigen = document.getElementById('lbl-origen');
    const lblTablasCount = document.getElementById('lbl-tablas-count');
    const btnStartTransfer = document.getElementById('btn-start-transfer');
    const consoleOutput = document.getElementById('console-output');
    
    // Modal Elements
    const modal = document.getElementById('modal-add-conn');
    const btnAddConn = document.getElementById('btn-add-conn');
    const spanClose = document.querySelector('.close-modal');
    const formAddConn = document.getElementById('form-add-conn');

    // Tabs Elements
    const tabBtns = document.querySelectorAll('.tab-btn');
    const sshGroup = document.getElementById('ssh-group');
    const tipoConexionInput = document.getElementById('tipo_conexion');
    const mysqlHostInput = document.getElementById('mysql_host');

    // Lógica de Pestañas (Tabs)
    tabBtns.forEach(btn => {
        btn.onclick = () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const tab = btn.getAttribute('data-tab');
            tipoConexionInput.value = tab;
            
            if (tab === 'local') {
                sshGroup.style.display = 'block';
                document.getElementById('ssh_host').required = true;
                document.getElementById('ssh_user').required = true;
                if(!mysqlHostInput.value) mysqlHostInput.value = '127.0.0.1';
            } else {
                sshGroup.style.display = 'none';
                document.getElementById('ssh_host').required = false;
                document.getElementById('ssh_user').required = false;
                if(mysqlHostInput.value === '127.0.0.1') mysqlHostInput.value = '';
            }
        };
    });

    // Inicializar
    loadConnections();

    // Eventos Modal
    btnAddConn.onclick = () => modal.style.display = 'block';
    spanClose.onclick = () => modal.style.display = 'none';
    window.onclick = (e) => { if (e.target === modal) modal.style.display = 'none'; }

    // Evento Formulario Conexión
    formAddConn.onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(formAddConn);
        const data = Object.fromEntries(formData.entries());
        
        try {
            const res = await fetch('/api/connections', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await res.json();
            if(res.ok) {
                modal.style.display = 'none';
                formAddConn.reset();
                loadConnections();
            } else {
                alert(result.error);
            }
        } catch (error) {
            console.error('Error:', error);
        }
    };

    // Cargar Conexiones
    async function loadConnections() {
        try {
            const res = await fetch('/api/connections');
            connections = await res.json();
            renderTree();
            updateDestSelect();
        } catch(e) { console.error(e); }
    }

    // Renderizar Árbol
    function renderTree() {
        treeContainer.innerHTML = '';
        connections.forEach(conn => {
            const node = document.createElement('div');
            node.className = 'tree-node';
            
            const title = document.createElement('div');
            title.className = 'tree-node-title';
            title.innerHTML = `<span>🗄️ ${conn.name}</span>`;
            
            const childrenContainer = document.createElement('div');
            childrenContainer.className = 'tree-children';
            childrenContainer.id = `children-${conn.id}`;

            title.onclick = () => toggleNode(conn, childrenContainer);

            node.appendChild(title);
            node.appendChild(childrenContainer);
            treeContainer.appendChild(node);
        });
    }

    function updateDestSelect() {
        destSelect.innerHTML = '<option value="">-- Seleccionar --</option>';
        connections.forEach(conn => {
            const opt = document.createElement('option');
            opt.value = conn.id;
            opt.textContent = conn.name;
            destSelect.appendChild(opt);
        });
    }

    async function toggleNode(conn, container) {
        if (container.classList.contains('active')) {
            container.classList.remove('active');
            return;
        }

        // Si ya tiene elementos, solo mostramos
        if (container.children.length > 0) {
            container.classList.add('active');
            return;
        }

        // Cargar Tablas
        container.innerHTML = '<i>Cargando tablas...</i>';
        container.classList.add('active');

        try {
            const res = await fetch(`/api/tables/${conn.id}`);
            const tables = await res.json();
            
            if(tables.error) {
                container.innerHTML = `<span style="color:red">${tables.error}</span>`;
                return;
            }

            container.innerHTML = '';
            tables.forEach(table => {
                const item = document.createElement('div');
                item.className = 'tree-item';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.value = table;
                checkbox.onchange = (e) => handleTableSelection(e, conn.id, table);

                item.appendChild(checkbox);
                item.appendChild(document.createTextNode(table));
                container.appendChild(item);
            });
        } catch(e) {
            container.innerHTML = `<span style="color:red">Error cargando tablas</span>`;
        }
    }

    function handleTableSelection(e, connId, table) {
        if (selectedOrigenId !== null && selectedOrigenId !== connId) {
            alert("Solo puedes seleccionar tablas de un único Origen a la vez.");
            e.target.checked = false;
            return;
        }

        if (e.target.checked) {
            selectedOrigenId = connId;
            selectedTables.add(table);
        } else {
            selectedTables.delete(table);
            if (selectedTables.size === 0) selectedOrigenId = null;
        }

        updateUIStatus();
    }

    function updateUIStatus() {
        const origen = connections.find(c => c.id === selectedOrigenId);
        lblOrigen.textContent = origen ? origen.name : 'Ninguno';
        lblTablasCount.textContent = selectedTables.size;
        btnStartTransfer.disabled = selectedTables.size === 0 || !destSelect.value;
    }

    destSelect.onchange = updateUIStatus;

    // Iniciar Transferencia
    btnStartTransfer.onclick = async () => {
        const destId = destSelect.value;
        if(selectedOrigenId == destId) {
            alert("El origen y destino no pueden ser el mismo.");
            return;
        }

        const payload = {
            origen_id: selectedOrigenId,
            destino_id: parseInt(destId),
            tablas: Array.from(selectedTables)
        };

        btnStartTransfer.disabled = true;
        consoleOutput.innerHTML = '<p class="log-info">Iniciando petición al servidor...</p>';

        try {
            const res = await fetch('/api/transfer', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            if(data.task_id) {
                currentTaskId = data.task_id;
                startPolling();
            } else {
                appendLog(data.error || 'Error desconocido', 'error');
                btnStartTransfer.disabled = false;
            }
        } catch (e) {
            appendLog('Error de red al iniciar', 'error');
            btnStartTransfer.disabled = false;
        }
    };

    function startPolling() {
        if(pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(pollStatus, 2000);
    }

    async function pollStatus() {
        try {
            const res = await fetch(`/api/transfer_status/${currentTaskId}`);
            const data = await res.json();
            
            renderLogs(data.logs);
            
            if(data.status === 'Completed' || data.status === 'Failed') {
                clearInterval(pollInterval);
                btnStartTransfer.disabled = false;
                appendLog(`Tarea finalizada con estado: ${data.status}`, data.status === 'Completed' ? 'success' : 'error');
            }
        } catch(e) {
            console.error('Polling error', e);
        }
    }

    function renderLogs(logs) {
        consoleOutput.innerHTML = '';
        logs.forEach(log => {
            appendLog(log);
        });
    }

    function appendLog(msg, type='info') {
        const p = document.createElement('p');
        p.textContent = msg;
        p.className = `log-${type}`;
        consoleOutput.appendChild(p);
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    }
});
