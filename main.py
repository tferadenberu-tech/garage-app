<!DOCTYPE html>
<html lang="am">
<head>
    <meta charset="UTF-8">
    <title>Steely RMI - Garage Maintenance Dashboard</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        /* ፎርሙ ላይ ያሉ መስኮች በንጽህና እንዲገለጡ እና መደራረብ እንዳይኖር */
        .card { border-radius: 10px; }
        .form-label { font-size: 0.85rem; font-weight: 600; color: #333; }
        .table-responsive { overflow-x: auto; }
    </style>
</head>
<body class="bg-secondary bg-opacity-10">
    <nav class="navbar navbar-dark bg-dark px-4 mb-4">
        <span class="navbar-brand mb-0 h1">Steely RMI Garage Maintenance Dashboard</span>
        <a href="/logout" class="btn btn-outline-light btn-sm">ውጣ (Logout)</a>
    </nav>

    <div class="container-fluid px-4">
        <!-- ቅጽ: አዲስ ጥገና ለመመዝገብ (Work Order Form) -->
        <div class="card shadow mb-4 p-4">
            <h4 class="text-primary mb-3">Create New Work Order</h4>
            <form action="/add" method="POST">
                <!-- 1ኛ ረድፍ: Serial Number, Work Order No, Vehicle Plate, Vehicle Type, Current Reading, Reading Unit -->
                <div class="row g-3 mb-3">
                    <div class="col-md-2">
                        <label class="form-label">Serial Number (S/N):</label>
                        <input type="text" name="serial_number" class="form-control form-control-sm" placeholder="e.g. SN-002">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Work Order No:</label>
                        <input type="text" name="work_order_no" class="form-control form-control-sm" placeholder="e.g. WO-202">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Vehicle Plate Number:</label>
                        <input type="text" name="vehicle_or_machine" class="form-control form-control-sm" placeholder="e.g. AA-3-12" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Vehicle Type / Model:</label>
                        <input type="text" name="vehicle_type" class="form-control form-control-sm" placeholder="e.g. Sino Truck">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Current Reading:</label>
                        <input type="number" step="0.1" name="current_km" class="form-control form-control-sm" value="0" required>
                    </div>
                    <div class="col-md-1">
                        <label class="form-label">Unit:</label>
                        <input type="text" class="form-control form-control-sm bg-light" value="KM (+5000)" readonly>
                    </div>
                </div>

                <!-- 2ኛ ረድፍ: Maintenance Type, Job Status, Driver Name, Assigned Technicians -->
                <div class="row g-3 mb-3">
                    <div class="col-md-3">
                        <label class="form-label">Maintenance Type:</label>
                        <select name="maintenance_type" class="form-select form-select-sm" required>
                            <option value="Preventive">PM (Preventive Maint.)</option>
                            <option value="Corrective">Corrective</option>
                            <option value="Breakdown">Breakdown</option>
                            <option value="Routine Service">Routine Service</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Job Status:</label>
                        <select name="job_status" class="form-select form-select-sm">
                            <option value="Completed">Completed</option>
                            <option value="Pending">Pending</option>
                            <option value="In Progress">In Progress</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Driver Name:</label>
                        <input type="text" name="driver_name" class="form-control form-control-sm" placeholder="e.g. አበበ በለጤ">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Assigned Technicians:</label>
                        <input type="text" name="technicians" class="form-control form-control-sm" placeholder="e.g., Ato Mihret">
                    </div>
                </div>

                <!-- 3ኛ ረድፍ: Start Date, End Date -->
                <div class="row g-3 mb-3">
                    <div class="col-md-6">
                        <label class="form-label">Start Date & Time:</label>
                        <input type="datetime-local" name="start_date" class="form-control form-control-sm">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">End Date & Time:</label>
                        <input type="datetime-local" name="end_date" class="form-control form-control-sm">
                    </div>
                </div>

                <!-- 4ኛ ረድፍ: Work Description -->
                <div class="mb-3">
                    <label class="form-label">Work Description:</label>
                    <textarea name="description" class="form-control form-control-sm" rows="2" placeholder="e.g. Maintenance details and diagnostics note"></textarea>
                </div>

                <!-- ማስቀመጫ ቁልፍ -->
                <div class="text-end">
                    <button type="submit" class="btn btn-success btn-sm px-4">💾 Save Work Order</button>
                </div>
            </form>
        </div>

        <!-- ሠንጠረዥ: መዝገቦችን ለማሳየት (Dashboard Table) -->
        <div class="card shadow p-4">
            <h4 class="text-dark mb-3">Maintenance Execution & Work Time Log</h4>
            <div class="table-responsive">
                <table class="table table-striped table-bordered align-middle mt-2 text-center">
                    <thead class="table-dark">
                        <tr>
                            <th>Serial No (S/N)</th>
                            <th>WO #</th>
                            <th>Plate No</th>
                            <th>Vehicle Type</th>
                            <th>Maint. Type</th>
                            <th>Status</th>
                            <th>Assigned Technicians</th>
                            <th>Start Time</th>
                            <th>End Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for rec in records %}
                        <tr>
                            <td>{{ rec.id }}</td>
                            <td>{{ rec.work_order_no | default('WO-001') }}</td>
                            <td>{{ rec.vehicle_or_machine }}</td>
                            <td>{{ rec.vehicle_type | default('-') }}</td>
                            <td><span class="badge bg-info text-dark">{{ rec.maintenance_type }}</span></td>
                            <td><span class="badge bg-success">Completed</span></td>
                            <td>{{ rec.technicians | default('-') }}</td>
                            <td>{{ rec.start_date | default('-') }}</td>
                            <td>{{ rec.end_date | default('-') }}</td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="9" class="text-muted">ምንም የተመዘገበ መረጃ የለም።</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
