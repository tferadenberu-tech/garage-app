<td class="small">{{ "{:,.2f}".format(log.battery_cost) }} ETB</td>
                                <td class="small">{{ "{:,.2f}".format(log.lubrication_cost) }} ETB</td>
                                <td class="small">{{ "{:,.2f}".format(log.tire_cost) }} ETB</td>
                                <td class="text-center">
                                    <a href="/delete_log/{{ log.id }}" class="btn btn-outline-danger btn-sm px-2 py-0 fw-bold" onclick="return confirm('Delete this work log entry?');">✕</a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

        </div>
    </div>
</div>

<!-- Modal: Spare Inventory -->
<div class="modal fade" id="inventoryModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header bg-primary text-white">
                <h5 class="modal-title fw-bold">⚙️ SteelY R.M.I Spare Inventory & Stock Management</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="table-responsive">
                    <table class="table table-bordered table-sm align-middle">
                        <thead class="table-water-blue">
                            <tr>
                                <th>ID</th>
                                <th>Part Name</th>
                                <th>Specification</th>
                                <th>For Vehicle</th>
                                <th>Qty in Stock</th>
                                <th>Unit Price (ETB)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for part in inventory %}
                            <tr>
                                <td class="fw-bold">{{ part.id }}</td>
                                <td class="fw-bold text-primary">{{ part.part_name }}</td>
                                <td class="small">{{ part.spec }}</td>
                                <td><span class="badge bg-secondary">{{ part.for_vehicle }}</span></td>
                                <td class="fw-bold">{{ part.qty }}</td>
                                <td class="fw-bold text-success">{{ "{:,.2f}".format(part.unit_price) }} ETB</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
function addSpareRow() {
    const container = document.getElementById("spare-rows-container");
    const newRow = document.createElement("div");
    newRow.className = "row g-2 spare-row mb-2 align-items-center";
    newRow.innerHTML = `
        <div class="col-md-3">
            <input type="text" name="spare_name[]" class="form-control form-control-sm" placeholder="Spare Part Name" required>
        </div>
        <div class="col-md-3">
            <input type="text" name="spare_spec[]" class="form-control form-control-sm" placeholder="Specification" required>
        </div>
        <div class="col-md-1">
            <input type="number" name="spare_qty[]" class="form-control form-control-sm spare-qty" placeholder="Qty" value="1" min="1" required oninput="calculateRowTotal(this)">
        </div>
        <div class="col-md-2">
            <input type="number" step="0.01" name="spare_price[]" class="form-control form-control-sm spare-price" placeholder="Unit Price (ETB)" value="0.00" required oninput="calculateRowTotal(this)">
        </div>
        <div class="col-md-2">
            <span class="small fw-bold text-success row-total-text">0.00 ETB</span>
        </div>
        <div class="col-md-1">
            <button type="button" class="btn btn-outline-danger btn-sm w-100" onclick="removeSpareRow(this)">✕</button>
        </div>
    `;
    container.appendChild(newRow);
}

function removeSpareRow(btn) {
    const row = btn.closest(".spare-row");
    if (document.querySelectorAll(".spare-row").length > 1) {
        row.remove();
    } else {
        alert("At least one spare row placeholder should remain.");
    }
}

function calculateRowTotal(element) {
    const row = element.closest(".spare-row");
    const qty = parseFloat(row.querySelector(".spare-qty").value) || 0;
    const price = parseFloat(row.querySelector(".spare-price").value) || 0;
    const total = qty * price;
    row.querySelector(".row-total-text").innerText = total.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + " ETB";
}
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    if "user" not in session:
        session["user"] = {"name": "Demberu Tefera", "role": "Head of Workshop"}
    
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    
    logs = garage_data["maintenance_logs"]
    
    # Filtering logic
    filtered_logs = logs
    if start_date and end_date:
        filtered_logs = [
            l for l in logs 
            if start_date <= l["start_time"].split(" ")[0] <= end_date
        ]
        
    def aggregate_metrics(log_list):
        total_jobs = len(log_list)
        pm_jobs = sum(1 for l in log_list if l["maintenance_type"] == "PM")
        cm_jobs = sum(1 for l in log_list if l["maintenance_type"] == "CM")
        inspection_jobs = sum(1 for l in log_list if l["maintenance_type"] == "Inspection")
        total_work_hours = sum(l["effective_hours"] for l in log_list)
        
        total_spare_qty = sum(sum(sp["qty"] for sp in l.get("replaced_spares", [])) for l in log_list)
        total_spares_cost = sum(sum(sp["total_cost"] for sp in l.get("replaced_spares", [])) for l in log_list)
        
        total_lubrication_qty = sum(l.get("lubrication_qty", 0.0) for l in log_list)
        total_lubrication_cost = sum(l.get("lubrication_cost", 0.0) for l in log_list)
        
        total_battery_cost = sum(l.get("battery_cost", 0.0) for l in log_list)
        total_tire_cost = sum(l.get("tire_cost", 0.0) for l in log_list)
        
        total_expenditure = total_spares_cost + total_lubrication_cost + total_battery_cost + total_tire_cost
        
        return {
            "total_jobs": total_jobs,
            "pm_jobs": pm_jobs,
            "cm_jobs": cm_jobs,
            "inspection_jobs": inspection_jobs,
            "total_work_hours": round(total_work_hours, 2),
            "total_spare_qty": total_spare_qty,
            "total_spares_cost": total_spares_cost,
            "total_lubrication_qty": total_lubrication_qty,
            "total_lubrication_cost": total_lubrication_cost,
            "total_battery_cost": total_battery_cost,
            "total_tire_cost": total_tire_cost,
            "total_expenditure": total_expenditure
        }

    # Weekly and Monthly summaries based on overall logs or filtered dataset
    weekly = aggregate_metrics(logs[-7:]) if logs else aggregate_metrics([])
    monthly = aggregate_metrics(logs[-30:]) if logs else aggregate_metrics([])
    
    return render_template_string(
        HTML_TEMPLATE,
        user=session["user"],
        weekly=weekly,
        monthly=monthly,
        logs=filtered_logs,
        inventory=garage_data["spare_parts"]
    )

@app.route("/add_work_order", methods=["POST"])
def add_work_order():
    sn = request.form.get("sn")
    wo_no = request.form.get("wo_no")
    vehicle = request.form.get("vehicle")
    model = request.form.get("model")
    reading_value = int(request.form.get("reading_value", 0))
    reading_unit = request.form.get("reading_unit", "KM")
    next_service = calculate_next_service(reading_value, reading_unit)
    driver = request.form.get("driver")
    technicians = request.form.get("technicians")
    maintenance_type = request.form.get("maintenance_type")
    work_status = request.form.get("work_status")
    start_time = request.form.get("start_time").replace("T", " ")
    finish_time = request.form.get("finish_time").replace("T", " ")
    effective_hours = calculate_effective_hours(request.form.get("start_time"), request.form.get("finish_time"))
    description = request.form.get("description")
    
    # Parse dynamic spare parts
    spare_names = request.form.getlist("spare_name[]")
    spare_specs = request.form.getlist("spare_spec[]")
    spare_qtys = request.form.getlist("spare_qty[]")
    spare_prices = request.form.getlist("spare_price[]")
    
    replaced_spares = []
    for i in range(len(spare_names)):
        if spare_names[i].strip():
            q = int(spare_qtys[i]) if i < len(spare_qtys) else 1
            p = float(spare_prices[i]) if i < len(spare_prices) else 0.0
            replaced_spares.append({
                "part_name": spare_names[i],
                "spec": spare_specs[i] if i < len(spare_specs) else "",
                "qty": q,
                "unit_price": p,
                "total_cost": q * p
            })
            
    battery_qty = int(request.form.get("battery_qty", 0))
    battery_cost = float(request.form.get("battery_cost", 0.0))
    lubrication_qty = float(request.form.get("lubrication_qty", 0.0))
    lubrication_cost = float(request.form.get("lubrication_cost", 0.0))
    tire_qty = int(request.form.get("tire_qty", 0))
    tire_cost = float(request.form.get("tire_cost", 0.0))
    
    new_id = max([l["id"] for l in garage_data["maintenance_logs"]], default=0) + 1
    
    new_log = {
        "id": new_id,
        "sn": sn,
        "wo_no": wo_no,
        "vehicle": vehicle,
        "model": model,
        "reading_value": reading_value,
        "reading_unit": reading_unit,
        "next_service": next_service,
        "driver": driver,
        "technicians": technicians,
        "maintenance_type": maintenance_type,
        "work_status": work_status,
        "start_time": start_time,
        "finish_time": finish_time,
        "effective_hours": effective_hours,
        "description": description,
        "replaced_spares": replaced_spares,
        "battery_qty": battery_qty,
        "battery_cost": battery_cost,
        "lubrication_qty": lubrication_qty,
        "lubrication_cost": lubrication_cost,
        "tire_qty": tire_qty,
        "tire_cost": tire_cost
    }
    
    garage_data["maintenance_logs"].append(new_log)
    return redirect(url_for("index"))

@app.route("/delete_log/<int:log_id>", methods=["GET"])
def delete_log(log_id):
    garage_data["maintenance_logs"] = [l for l in garage_data["maintenance_logs"] if l["id"] != log_id]
    return redirect(url_for("index"))

@app.route("/reset_all_logs", methods=["GET"])
def reset_all_logs():
    garage_data["maintenance_logs"] = []
    return redirect(url_for("index"))

@app.route("/export/master_excel", methods=["GET"])
def export_master_excel():
    df = pd.DataFrame(garage_data["maintenance_logs"])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Master_Garage_Logs")
    output.seek(0)
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="SteelY_Garage_Master_Report.xlsx")

@app.route("/export/execution_excel", methods=["GET"])
def export_execution_excel():
    return redirect(url_for("export_master_excel"))

@app.route("/logout", methods=["GET"])
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
