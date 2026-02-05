<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sincronización BCV - Odoo</title>
    <!-- PWA -->
    <link rel="manifest" href="manifest.json">
    <link rel="apple-touch-icon" href="imagen/favicon/apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="32x32" href="imagen/favicon/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="imagen/favicon/favicon-16x16.png">
    <meta name="theme-color" content="#2196F3">
    <!-- Materialize CSS -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
        body { font-family: 'Roboto', sans-serif; background-color: #f5f5f5; }
        .brand-logo { font-weight: 300; }
        .card-panel { border-radius: 8px; }
        .btn-large { border-radius: 25px; }
        #log-area { 
            background: #333; 
            color: #0f0; 
            padding: 15px; 
            border-radius: 4px; 
            height: 300px; 
            overflow-y: auto; 
            font-family: monospace; 
            font-size: 0.9rem;
        }
        .header-bg {
            background: linear-gradient(45deg, #1565c0, #42a5f5);
            padding: 20px 0;
            margin-bottom: 20px;
            color: white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }

        /* Mobile Optimizations */
        @media only screen and (max-width: 600px) {
            .header-bg {
                padding: 10px 0; /* Narrower header */
                margin-bottom: 10px;
            }
            .header-bg h4 {
                font-size: 1.5rem; /* Smaller title */
                margin: 0.5rem 0;
            }
            .header-bg p {
                font-size: 0.9rem;
                margin: 0;
            }
            .container {
                width: 95%; /* More width for content */
            }
            table.highlight th, table.highlight td {
                padding: 5px 2px; /* Compact table cells */
                font-size: 0.85rem; /* Smaller table text */
            }
            .card .card-content {
                padding: 10px; /* Reduce card padding */
            }
            .card-title {
                margin-bottom: 5px !important; /* Reduce space after "Estado del Sistema" */
                font-size: 1.2rem !important;
            }
            #status-loading {
                padding: 10px !important; /* Reduce loading padding */
            }
            h5 {
                font-size: 1.1rem; /* Smaller subtitles */
                margin: 0.5rem 0; /* Tighten spacing */
            }
            .btn-large {
                height: 40px;
                line-height: 40px;
                font-size: 0.9rem;
            }
            /* Ensure table fits */
            .card-content table {
                width: 100%;
                display: table;
            }
        }
    </style>
</head>
<body>

    <div class="header-bg center-align">
        <h4><i class="material-icons large-text">sync</i> Actualizador BCV > Odoo</h4>
        <p>Sincronización automática de tasa de cambio</p>
    </div>

    <div class="container">
        <!-- Status Section -->
        <div class="row">
            <div class="col s12 m8 offset-m2">
                <div class="card hoverable">
                    <div class="card-content">
                        
                        <div id="status-loading" class="center-align" style="padding: 20px;">
                             <div class="preloader-wrapper active">
                                <div class="spinner-layer spinner-blue-only">
                                  <div class="circle-clipper left"><div class="circle"></div></div>
                                  <div class="gap-patch"><div class="circle"></div></div>
                                  <div class="circle-clipper right"><div class="circle"></div></div>
                                </div>
                              </div>
                              <p>Verificando tasas...</p>
                        </div>

                        <div id="status-content" style="display:none;">
                            <div class="row center-align">
                                <div class="col s12">
                                    <h5 class="blue-text" style="font-weight:bold; margin-bottom:5px;">Tasa Dólar BCV = Bs. <span id="bcv-rate-display">--.--</span></h5>
                                    <p class="grey-text text-darken-1" style="margin-top:0; font-size: 1.1rem; font-weight: 500;" id="server-date-display">--/--/----</p>
                                </div>
                            </div>
                            
                            <table class="highlight">
                                <thead>
                                    <tr>
                                        <th>Compañía</th>
                                        <th>Tasa Actual</th>
                                        <th>Cálculo (Inv)</th>
                                        <th>Estado</th>
                                    </tr>
                                </thead>
                                <tbody id="companies-table-body">
                                </tbody>
                            </table>
                            
                            <div class="section center-align" style="margin-top: 20px;">
                                <p id="status-message" class="grey-text"></p>
                                <button id="btn-sync" class="btn-large waves-effect waves-light blue darken-2" onclick="runSync()" disabled>
                                    <i class="material-icons left">cloud_upload</i> Sincronizar Ahora
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col s12">
                <h5 class="grey-text text-darken-2"><i class="material-icons left">dvr</i> Log de Operaciones</h5>
                <div id="log-area">Esperando inicio...</div>
            </div>
        </div>
    </div>

    <!-- Materialize JS -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            checkStatus();
        });

        function checkStatus() {
            const loading = document.getElementById('status-loading');
            const content = document.getElementById('status-content');
            const btn = document.getElementById('btn-sync');
            const statusMsg = document.getElementById('status-message');
            const tbody = document.getElementById('companies-table-body');
            const bcvDisplay = document.getElementById('bcv-rate-display');
            const dateDisplay = document.getElementById('server-date-display');
            const log = document.getElementById('log-area');

            loading.style.display = 'block';
            content.style.display = 'none';

            fetch('run_script.php?action=status')
            .then(response => response.json())
            .then(data => {
                loading.style.display = 'none';
                content.style.display = 'block';

                if(data.success && data.output && data.output.success) {
                    const info = data.output;
                    // Format rate with comma for display
                    bcvDisplay.innerText = parseFloat(info.bcv_rate).toFixed(4).replace('.', ',');
                    dateDisplay.innerText = info.server_date || '--/--/----';
                    
                    tbody.innerHTML = '';
                    
                    if (info.companies && info.companies.length > 0) {
                        info.companies.forEach(comp => {
                            let icon = comp.match ? '<i class="material-icons green-text">check_circle</i>' : '<i class="material-icons red-text">cancel</i>';
                            let rowClass = comp.match ? '' : 'red lighten-5';
                            
                            let rateDisplay = parseFloat(comp.current_rate).toFixed(4);
                            if (comp.rate_date) {
                                rateDisplay += ` <small class='grey-text'>(${comp.rate_date})</small>`;
                            }
                            let calcInfo = comp.target_currency === 'USD' ? `(1/${info.bcv_rate})` : '=BCV';

                            let html = `<tr class="${rowClass}">
                                <td>${comp.company}</td>
                                <td>${comp.target_currency} ${rateDisplay}</td>
                                <td class="grey-text text-darken-1"><small>${calcInfo}</small></td>
                                <td>${icon}</td>
                            </tr>`;
                            tbody.innerHTML += html;
                        });
                    } else {
                        tbody.innerHTML = '<tr><td colspan="4" class="center-align">No se encontraron compañías</td></tr>';
                    }

                    if (info.all_match) {
                        btn.disabled = true;
                        statusMsg.innerHTML = '<i class="material-icons tiny">check</i> Sistema actualizado. Las tasas coinciden.';
                        statusMsg.className = "green-text text-darken-2";
                        log.innerHTML += "<br>> Verificación: Todo al día.";
                    } else {
                        btn.disabled = false;
                        statusMsg.innerHTML = '<i class="material-icons tiny">warning</i> Se detectaron diferencias. Actualización requerida.';
                        statusMsg.className = "red-text text-darken-2";
                        log.innerHTML += "<br>> Verificación: Se requieren actualizaciones.";
                    }

                } else {
                    const err = data.error || (data.output ? data.output.message : 'Error desconocido');
                    log.innerHTML += `<br>> [ERROR SYSTEM] ${err}`;
                    statusMsg.innerText = "Error obteniendo estado.";
                }
            })
            .catch(err => {
                loading.style.display = 'none';
                log.innerHTML += `<br>> [FATAL] ${err}`;
            });
        }

        function runSync() {
            const btn = document.getElementById('btn-sync');
            const log = document.getElementById('log-area');
            
            if(!confirm("¿Está seguro de actualizar las tasas para las compañías marcadas?")) return;

            btn.classList.add('disabled');
            btn.innerHTML = '<i class="material-icons left">autorenew</i> Actualizando...';
            log.innerHTML += "<br>> Iniciando actualización...";

            fetch('run_script.php?action=update')
            .then(response => response.json())
            .then(data => {
                
                if(data.success && data.output) {
                    log.innerHTML += `<br>> <strong>Proceso finalizado.</strong>`;
                    
                    if (data.output.result && data.output.result.log) {
                        data.output.result.log.forEach(line => {
                            log.innerHTML += `<br>> [ODOO] ${line}`;
                        });
                    }
                    if (data.output.result && !data.output.result.success) {
                         log.innerHTML += `<br>> [ERROR ODOO] ${data.output.result.message}`;
                    }

                    log.innerHTML += "<br>> <span style='color:cyan'>Recargando estado...</span>";
                    
                    // Reload status after short delay
                    setTimeout(() => {
                        btn.innerHTML = '<i class="material-icons left">cloud_upload</i> Sincronizar Ahora';
                        checkStatus();
                    }, 2000);

                } else {
                    log.innerHTML += `<br>> [ERROR SISTEMA] ${data.error}`;
                    btn.classList.remove('disabled');
                    btn.innerHTML = '<i class="material-icons left">cloud_upload</i> Reintentar';
                }
                
                log.scrollTop = log.scrollHeight;
            })
            .catch(err => {
                btn.classList.remove('disabled');
                btn.innerHTML = 'Reintentar';
                log.innerHTML += `<br>> [ERROR FATAL] ${err}`;
            });
        }
    </script>
</body>
</html>
